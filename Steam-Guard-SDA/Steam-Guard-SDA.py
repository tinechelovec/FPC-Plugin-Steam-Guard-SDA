from __future__ import annotations
from typing import TYPE_CHECKING
import os
import json
import base64
import hmac
import time
import logging
from telebot.types import Message , InlineKeyboardButton
from locales.localizer import Localizer
from FunPayAPI.updater.events import NewMessageEvent
from tg_bot import keyboards


if TYPE_CHECKING:
    from cardinal import Cardinal

logger = logging.getLogger("SteamGuardSDA")
localizer = Localizer()
_ = localizer.translate

NAME = "Steam Guard (SDA)"
VERSION = "1.0"
DESCRIPTION = "Получение Steam Guard (SDA) кода по команде."
CREDITS = "@tinechelovec"
UUID = "b886288e-7908-4f62-bd48-48e1a5c7a8e5"
SETTINGS_PAGE = False

PLUGIN_FOLDER = "storage/plugins/steam_guard_sda"
DATA_FILE = os.path.join(PLUGIN_FOLDER, "data.json")
os.makedirs(PLUGIN_FOLDER, exist_ok=True)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f, indent=4, ensure_ascii=False)

user_states = {}

def load_data() -> dict:
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- Генерация кода SDA ---
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

# --- FSM обработка SDA аккаунтов ---
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

    text = message.text.strip()

    
    if text.startswith("/"):
        user_states.pop(chat_id)
        cardinal.telegram.bot.send_message(chat_id, "❌ Операция отменена, так как вы ввели команду.")
        return

    state = user_states[chat_id]
    text = message.text.strip()
    data = load_data()
    uid = str(chat_id)

    # --- Удаление аккаунта ---
    if state["step"] == "del_target":
        target = text.lower()
        if uid not in data or not data[uid]:
            cardinal.telegram.bot.send_message(chat_id, "❌ У вас нет добавленных аккаунтов.")
        else:
            before_len = len(data[uid])
            data[uid] = [
                acc for acc in data[uid]
                if acc["command"].lower() != target and acc["name"].lower() != target
            ]
            if len(data[uid]) < before_len:
                save_data(data)
                cardinal.telegram.bot.send_message(chat_id, "✅ Аккаунт удалён.")
            else:
                cardinal.telegram.bot.send_message(chat_id, "❌ Аккаунт не найден.")
        user_states.pop(chat_id)
        return

    # --- SDA добавление аккаунта ---
    if state["step"] == "secret":
        shared_secret = text
        test_code = generate_steam_guard_code(shared_secret)
        if not test_code:
            cardinal.telegram.bot.send_message(chat_id, "❌ Невалидный shared_secret. Код не удалось сгенерировать.")
            user_states.pop(chat_id)
            return
        state["shared_secret"] = shared_secret
        state["step"] = "name"
        cardinal.telegram.bot.send_message(chat_id, "🏷 Введите название аккаунта (например, 'Мой основной'):")

    elif state["step"] == "name":
        state["name"] = text.strip()
        state["step"] = "command"
        cardinal.telegram.bot.send_message(chat_id, "⌨️ Введите команду, по которой вы будете получать код (например: !steam):")

    elif state["step"] == "command":
        cmd = text.strip().lower()
        reserved_commands = ["/addsda", "/delsda", "/listsda"]
        reserved_names = [c.lstrip("/") for c in reserved_commands]

        existing_commands = [acc["command"].lower() for acc in data.get(uid, [])]

        if cmd in reserved_names or cmd in reserved_commands:
            cardinal.telegram.bot.send_message(chat_id, "❌ Эту команду нельзя использовать, она зарезервирована.")
            user_states.pop(chat_id)
            return

        if cmd in existing_commands:
            cardinal.telegram.bot.send_message(chat_id, "❌ Такая команда уже используется.")
            user_states.pop(chat_id)
            return


        data.setdefault(uid, []).append({
            "name": state["name"],
            "command": cmd,
            "shared_secret": state["shared_secret"]
        })
        save_data(data)

        cardinal.telegram.bot.send_message(
            chat_id,
            f"✅ SDA-аккаунт добавлен.\n📛 Название: <code>{state['name']}</code>\n💬 Команда: <code>{cmd}</code>",
            parse_mode="HTML"
        )
        user_states.pop(chat_id)


# --- Список аккаунтов ---
def listsda_handler(message: Message, cardinal: Cardinal):
    uid = str(message.chat.id)
    data = load_data()
    if uid not in data or not data[uid]:
        cardinal.telegram.bot.send_message(message.chat.id, "❌ У вас нет добавленных аккаунтов.")
        return
    text = "📜 Ваши SDA-аккаунты:\n\n" + "\n".join(
        f"🏷 <code>{acc['name']}</code> — команда: <code>{acc['command']}</code>"
        for acc in data[uid]
    )
    cardinal.telegram.bot.send_message(message.chat.id, text, parse_mode="HTML")

# --- Обработка сообщений от FunPay ---
def new_message_handler(cardinal: Cardinal, event: NewMessageEvent):
    chat_id = str(event.message.chat_id)
    data = load_data()

    for uid, accounts in data.items():
        for acc in accounts:
            if event.message.text.strip().lower() == acc["command"].lower():
                code = generate_steam_guard_code(acc["shared_secret"])
                if code:
                    cardinal.account.send_message(event.message.chat_id, f"✅ Ваш код: {code}")
                else:
                    cardinal.account.send_message(event.message.chat_id, "❌ Ошибка генерации кода.")
                return

# --- Инициализация плагина ---
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