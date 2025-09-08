from __future__ import annotations
from typing import TYPE_CHECKING
import os
import json
import base64
import hmac
import time
import logging
from telebot.types import Message, InlineKeyboardButton
from locales.localizer import Localizer
from FunPayAPI.updater.events import NewMessageEvent
from tg_bot import keyboards

if TYPE_CHECKING:
    from cardinal import Cardinal

logger = logging.getLogger("SteamGuardSDA")
localizer = Localizer()
_ = localizer.translate

NAME = "Steam Guard (SDA)"
VERSION = "1.1"
DESCRIPTION = "Получение Steam Guard (SDA) кода по команде."
CREDITS = "@tinechelovec"
UUID = "b886288e-7908-4f62-bd48-48e1a5c7a8e5"
SETTINGS_PAGE = False

PLUGIN_FOLDER = "storage/plugins/steam_guard_sda"
DATA_FILE = os.path.join(PLUGIN_FOLDER, "data.json")
USAGE_FILE = os.path.join(PLUGIN_FOLDER, "usage.json")

os.makedirs(PLUGIN_FOLDER, exist_ok=True)
for fpath, default in [(DATA_FILE, {}), (USAGE_FILE, {})]:
    if not os.path.exists(fpath):
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=4, ensure_ascii=False)

user_states = {}

def load_data() -> dict:
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"load_data error: {e}")
        return {}

def save_data(data: dict):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"save_data error: {e}")

def load_usage() -> dict:
    try:
        with open(USAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"load_usage error: {e}")
        return {}

def save_usage(data: dict):
    try:
        with open(USAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"save_usage error: {e}")

def generate_steam_guard_code(shared_secret: str):
    try:
        key = base64.b64decode(shared_secret)
        timestamp = int(time.time()) // 30
        msg = timestamp.to_bytes(8, byteorder="big")
        hmac_result = hmac.new(key, msg, digestmod="sha1").digest()
        offset = hmac_result[-1] & 0xF
        code_bytes = hmac_result[offset:offset + 4]
        full_code = int.from_bytes(code_bytes, byteorder="big") & 0x7FFFFFFF
        chars = "23456789BCDFGHJKMNPQRTVWXY"
        code = ""
        for _ in range(5):
            code += chars[full_code % len(chars)]
            full_code //= len(chars)
        return code
    except Exception as e:
        logger.error(f"Ошибка генерации кода: {str(e)}")
        return None

orig_edit_plugin = keyboards.edit_plugin
def custom_edit_plugin(c, uuid, offset=0, ask_to_delete=False):
    kb = orig_edit_plugin(c, uuid, offset, ask_to_delete)
    if uuid == UUID:
        dev_btn = InlineKeyboardButton(text="👽 Разработчик", url=f"https://t.me/{CREDITS[1:]}")
        kb.keyboard[0] = [dev_btn]
    return kb
keyboards.edit_plugin = custom_edit_plugin

def addsda_start(message: Message, cardinal: Cardinal):
    user_states[message.chat.id] = {"step": "secret"}
    cardinal.telegram.bot.send_message(message.chat.id, "🔐 Введите ваш shared_secret:")

def delsda_start(message: Message, cardinal: Cardinal):
    user_states[message.chat.id] = {"step": "del_target"}
    cardinal.telegram.bot.send_message(message.chat.id, "🗑 Введите команду или название аккаунта для удаления:")

def handle_fsm_step(message: Message, cardinal: Cardinal):
    chat_id = message.chat.id
    if chat_id not in user_states:
        return
    text = (message.text or "").strip()
    if not text:
        return

    if text.startswith("/"):
        user_states.pop(chat_id)
        cardinal.telegram.bot.send_message(chat_id, "❌ Операция отменена.")
        return

    state = user_states[chat_id]
    data = load_data()
    uid = str(chat_id)

    if state["step"] == "del_target":
        target = text.lower()
        if uid not in data or not data[uid]:
            cardinal.telegram.bot.send_message(chat_id, "❌ У вас нет аккаунтов.")
        else:
            before = len(data[uid])
            data[uid] = [
                acc for acc in data[uid]
                if acc["command"].lower() != target and acc["name"].lower() != target
            ]
            if len(data[uid]) < before:
                save_data(data)
                cardinal.telegram.bot.send_message(chat_id, "✅ Аккаунт удалён.")
            else:
                cardinal.telegram.bot.send_message(chat_id, "❌ Аккаунт не найден.")
        user_states.pop(chat_id)
        return

    if state["step"] == "secret":
        shared_secret = text
        if not generate_steam_guard_code(shared_secret):
            cardinal.telegram.bot.send_message(chat_id, "❌ Невалидный shared_secret.")
            user_states.pop(chat_id)
            return
        state["shared_secret"] = shared_secret
        state["step"] = "name"
        cardinal.telegram.bot.send_message(chat_id, "🏷 Введите название аккаунта:")
        return

    if state["step"] == "name":
        state["name"] = text
        state["step"] = "command"
        cardinal.telegram.bot.send_message(chat_id, "⌨️ Введите команду (например: !steam):")
        return

    if state["step"] == "command":
        cmd = text.lower()
        reserved = ["/addsda", "/delsda", "/listsda"]
        if cmd in reserved or cmd in [c.lstrip("/") for c in reserved]:
            cardinal.telegram.bot.send_message(chat_id, "❌ Команда зарезервирована.")
            user_states.pop(chat_id)
            return
        if cmd in [acc["command"].lower() for acc in data.get(uid, [])]:
            cardinal.telegram.bot.send_message(chat_id, "❌ Такая команда уже существует.")
            user_states.pop(chat_id)
            return
        state["command"] = cmd
        state["step"] = "limit"
        cardinal.telegram.bot.send_message(chat_id, "🔢 Введите лимит (например: 5, '-' для безлимита):")
        return

    if state["step"] == "limit":
        raw = text
        if raw == "-":
            acc = {
                "name": state["name"], "command": state["command"],
                "shared_secret": state["shared_secret"], "limit": None, "period_hours": None
            }
            data.setdefault(uid, []).append(acc)
            save_data(data)
            cardinal.telegram.bot.send_message(
                chat_id,
                f"✅ SDA-аккаунт добавлен.\n"
                f"📛 Название: <code>{acc['name']}</code>\n"
                f"💬 Команда: <code>{acc['command']}</code>\n"
                f"🔢 Лимит: <code>без ограничений</code>",
                parse_mode="HTML"
            )
            user_states.pop(chat_id)
            return
        try:
            limit = int(raw)
            if limit <= 0:
                raise ValueError
        except ValueError:
            cardinal.telegram.bot.send_message(chat_id, "❌ Введите число или '-'.")
            return
        state["limit"] = limit
        state["step"] = "period"
        cardinal.telegram.bot.send_message(chat_id, "⏱ Введите период в часах (например: 24, '-' или 0 для навсегда):")
        return

    if state["step"] == "period":
        raw = text
        if raw in ["-", "0"]:
            acc = {
                "name": state["name"], "command": state["command"],
                "shared_secret": state["shared_secret"], "limit": state["limit"], "period_hours": None
            }
            data.setdefault(uid, []).append(acc)
            save_data(data)
            cardinal.telegram.bot.send_message(
                chat_id,
                f"✅ SDA-аккаунт добавлен.\n"
                f"📛 Название: <code>{acc['name']}</code>\n"
                f"💬 Команда: <code>{acc['command']}</code>\n"
                f"🔢 Лимит: <code>{acc['limit']} навсегда</code>",
                parse_mode="HTML"
            )
            user_states.pop(chat_id)
            return
        try:
            hours = int(raw)
            if hours <= 0:
                raise ValueError
        except ValueError:
            cardinal.telegram.bot.send_message(chat_id, "❌ Введите положительное число, либо '-' или 0.")
            return
        acc = {
            "name": state["name"], "command": state["command"],
            "shared_secret": state["shared_secret"], "limit": state["limit"], "period_hours": hours
        }
        data.setdefault(uid, []).append(acc)
        save_data(data)
        cardinal.telegram.bot.send_message(
            chat_id,
            f"✅ SDA-аккаунт добавлен.\n"
            f"📛 Название: <code>{acc['name']}</code>\n"
            f"💬 Команда: <code>{acc['command']}</code>\n"
            f"🔢 Лимит: <code>{acc['limit']} за {hours}ч</code>",
            parse_mode="HTML"
        )
        user_states.pop(chat_id)
        return

def listsda_handler(message: Message, cardinal: Cardinal):
    uid = str(message.chat.id)
    data = load_data()
    if uid not in data or not data[uid]:
        cardinal.telegram.bot.send_message(message.chat.id, "❌ У вас нет аккаунтов.")
        return
    lines = []
    for acc in data[uid]:
        if acc.get("limit") is None:
            limit_txt = "без ограничений"
        elif acc.get("period_hours") is None:
            limit_txt = f"{acc['limit']} навсегда"
        else:
            limit_txt = f"{acc['limit']} за {acc['period_hours']}ч"
        lines.append(
            f"🏷 <code>{acc['name']}</code> — "
            f"💬 <code>{acc['command']}</code> — "
            f"🔢 <code>{limit_txt}</code>"
        )
    cardinal.telegram.bot.send_message(
        message.chat.id,
        "📜 Ваши SDA-аккаунты:\n\n" + "\n".join(lines),
        parse_mode="HTML"
    )

def _get_text_from_event_message(event_msg) -> str:
    return (getattr(event_msg, "text", "") or "").strip()

def _get_buyer_id_from_event_message(event_msg) -> str:
    for attr in ("user_id", "from_id", "sender_id"):
        val = getattr(event_msg, attr, None)
        if val:
            return str(val if isinstance(val, (int, str)) else getattr(val, "id", ""))
    return str(getattr(event_msg, "chat_id", ""))

def _format_time_left(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h: return f"{h}ч {m}м"
    if m: return f"{m}м"
    return f"{s}с"

def new_message_handler(cardinal: Cardinal, event: NewMessageEvent):
    try:
        text = _get_text_from_event_message(event.message).lower()
        if not text:
            return
        buyer_id = _get_buyer_id_from_event_message(event.message)
        data = load_data()
        usage = load_usage()
        now = int(time.time())

        for uid, accounts in data.items():
            for acc in accounts:
                cmd = acc.get("command", "").lower()
                if not cmd or text != cmd:
                    continue

                limit, period_hours = acc.get("limit"), acc.get("period_hours")

                if limit is None:
                    code = generate_steam_guard_code(acc["shared_secret"])
                    if code:
                        cardinal.account.send_message(event.message.chat_id, f"✅ Ваш код: {code}")
                    else:
                        cardinal.account.send_message(event.message.chat_id, "❌ Ошибка генерации.")
                    return

                limit = int(limit)
                usage.setdefault(uid, {}).setdefault(buyer_id, {}).setdefault(cmd, {"count": 0})

                record = usage[uid][buyer_id][cmd]

                if period_hours is None:
                    if record["count"] >= limit:
                        cardinal.account.send_message(event.message.chat_id, f"❌ Лимит {limit} навсегда исчерпан.")
                        save_usage(usage)
                        return
                else:
                    period_seconds = int(period_hours) * 3600
                    record.setdefault("reset_time", now + period_seconds)
                    if now > record["reset_time"]:
                        record["count"] = 0
                        record["reset_time"] = now + period_seconds
                    if record["count"] >= limit:
                        seconds_left = int(record["reset_time"] - now)
                        cardinal.account.send_message(
                            event.message.chat_id,
                            f"❌ Лимит исчерпан. Новый запрос через {_format_time_left(seconds_left)}."
                        )
                        save_usage(usage)
                        return

                code = generate_steam_guard_code(acc["shared_secret"])
                if not code:
                    cardinal.account.send_message(event.message.chat_id, "❌ Ошибка генерации.")
                    return
                record["count"] += 1
                save_usage(usage)
                left = max(0, limit - record["count"])
                total_txt = "∞" if period_hours is None else str(limit)
                cardinal.account.send_message(
                    event.message.chat_id,
                    f"✅ Ваш код: {code}\n📊 Осталось: {left}/{total_txt}"
                )
                return
    except Exception as e:
        logger.exception(f"new_message_handler error: {e}")


def init_cardinal(cardinal: Cardinal):
    tg = cardinal.telegram
    tg.msg_handler(lambda m: addsda_start(m, cardinal), commands=["addsda"])
    tg.msg_handler(lambda m: delsda_start(m, cardinal), commands=["delsda"])
    tg.msg_handler(lambda m: handle_fsm_step(m, cardinal), func=lambda m: m.chat.id in user_states)
    tg.msg_handler(lambda m: listsda_handler(m, cardinal), commands=["listsda"])
    cardinal.add_telegram_commands(UUID, [
        ("addsda", "Добавить SDA аккаунт", True),
        ("delsda", "Удалить SDA аккаунт", True),
        ("listsda", "Список SDA аккаунтов", True)
    ])

BIND_TO_PRE_INIT = [init_cardinal]
BIND_TO_NEW_MESSAGE = [new_message_handler]
BIND_TO_DELETE = None
