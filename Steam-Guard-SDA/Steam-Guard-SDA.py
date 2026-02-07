from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Any, Optional, List
import os
import json
import base64
import hmac
import time
import logging
import re
import unicodedata
from html import escape
from datetime import datetime

from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from telebot.apihelper import ApiTelegramException

from FunPayAPI.updater.events import NewMessageEvent

if TYPE_CHECKING:
    from cardinal import Cardinal

NAME = "Steam Guard (SDA)"
VERSION = "1.2"
DESCRIPTION = "Получение Steam Guard (SDA) кода по команде."
CREDITS = "@tinechelovec"
UUID = "b886288e-7908-4f62-bd48-48e1a5c7a8e5"
SETTINGS_PAGE = True

logger = logging.getLogger("SteamGuardSDA")
PREFIX = "[SteamGuardSDA]"

INSTRUCTION_URL = f"https://teletype.in/@tinechelovec/Steam-Guard-SDA"

PLUGIN_FOLDER = "storage/plugins/steam_guard_sda"
DATA_FILE = os.path.join(PLUGIN_FOLDER, "data.json")
USAGE_FILE = os.path.join(PLUGIN_FOLDER, "usage.json")
LOGS_FILE = os.path.join(PLUGIN_FOLDER, "logs.json")

os.makedirs(PLUGIN_FOLDER, exist_ok=True)

for fpath, default in [(DATA_FILE, {}), (USAGE_FILE, {}), (LOGS_FILE, {})]:
    if not os.path.exists(fpath):
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=4, ensure_ascii=False)

try:
    import tg_bot.CBT as CBT
except Exception:
    class CBT:
        EDIT_PLUGIN = "PLUGIN_EDIT"
        PLUGIN_SETTINGS = "PLUGIN_SETTINGS"
        PLUGINS_LIST = "44"
        BACK = None

CBT_EDIT_PLUGIN = getattr(CBT, "EDIT_PLUGIN", "PLUGIN_EDIT")
CBT_PLUGIN_SETTINGS = getattr(CBT, "PLUGIN_SETTINGS", "PLUGIN_SETTINGS")
CBT_PLUGINS_LIST_OPEN = f"{getattr(CBT, 'PLUGINS_LIST', '44')}:0"
CBT_BACK = getattr(CBT, "BACK", None) or f"{UUID}:back"

CB_WELCOME = f"{UUID}:welcome"

CB_SETTINGS = f"{UUID}:settings"
CB_ADD = f"{UUID}:add"
CB_LIST = f"{UUID}:list"
CB_DEL_MENU = f"{UUID}:del_menu"
CB_DEL_PICK = f"{UUID}:del_pick"
CB_DEL_YES = f"{UUID}:del_yes"
CB_DEL_NO = f"{UUID}:del_no"

CB_LOGS = f"{UUID}:logs"
CB_TEMPLATE = f"{UUID}:template"
CB_CANCEL = f"{UUID}:cancel"

CB_DELETE_PLUGIN = f"{UUID}:del_plugin"
CB_DELETE_PLUGIN_YES = f"{UUID}:del_plugin_yes"
CB_DELETE_PLUGIN_NO = f"{UUID}:del_plugin_no"

_fsm: Dict[int, Dict[str, Any]] = {}

_INVIS_RE = re.compile(r"[\u200B-\u200F\u202A-\u202E\u2060-\u206F\uFE0E\uFE0F\u00AD]")

def _normalize_cmd(s: str) -> str:
    if not s:
        return ""

    s = unicodedata.normalize("NFKC", str(s))
    s = s.replace("\u00A0", " ")
    s = _INVIS_RE.sub("", s)

    out = []
    for ch in s:
        cat = unicodedata.category(ch)
        if cat in ("Cc", "Cf"):
            continue
        out.append(ch)

    s = "".join(out)
    s = "".join(ch for ch in s if not ch.isspace())
    return s.strip().lower()

def _load_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"{PREFIX} _load_json({path}) error: {e}")
        return {}

def _save_json(path: str, data: dict):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"{PREFIX} _save_json({path}) error: {e}")

def load_data() -> dict:
    return _load_json(DATA_FILE)

def save_data(data: dict):
    _save_json(DATA_FILE, data)

def load_usage() -> dict:
    return _load_json(USAGE_FILE)

def save_usage(data: dict):
    _save_json(USAGE_FILE, data)

def load_logs() -> dict:
    return _load_json(LOGS_FILE)

def save_logs(data: dict):
    _save_json(LOGS_FILE, data)

def _default_cfg() -> dict:
    return {
        "template": "✅ Ваш код: {code}\n📊 Осталось: {left}/{total}",
        "max_logs": 80,
    }

def _get_cfg(data: dict) -> dict:
    g = data.get("global")
    if isinstance(g, dict):
        base = _default_cfg()
        base.update(g)
        data["global"] = base
        return base
    data["global"] = _default_cfg()
    return data["global"]

def _set_cfg(cfg: dict):
    data = load_data()
    data["global"] = cfg
    save_data(data)

def _get_accounts_for(chat_id: int, data: dict) -> List[dict]:
    uid = str(chat_id)
    arr = data.get(uid)
    if isinstance(arr, list):
        return arr
    return []

def _set_accounts_for(chat_id: int, data: dict, accounts: List[dict]):
    data[str(chat_id)] = accounts

def _limit_text(acc: dict) -> str:
    if acc.get("limit") is None:
        return "без ограничений"
    if acc.get("period_hours") is None:
        return f"{acc['limit']} навсегда"
    return f"{acc['limit']} за {acc['period_hours']}ч"

def _mask_secret(s: str) -> str:
    if not s:
        return "—"
    t = s.strip()
    if len(t) <= 10:
        return "********"
    return t[:4] + "…" + t[-4:]

def _fmt_dt(ts: int) -> str:
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%d.%m.%Y %H:%M:%S")
    except Exception:
        return str(ts)

def _push_log(owner_uid: str, entry: dict):
    try:
        logs = load_logs()
        arr = logs.get(owner_uid)
        if not isinstance(arr, list):
            arr = []
        arr.append(entry)

        data = load_data()
        cfg = _get_cfg(data)
        max_logs = int(cfg.get("max_logs") or 80)
        if max_logs < 10:
            max_logs = 10

        if len(arr) > max_logs:
            arr = arr[-max_logs:]

        logs[owner_uid] = arr
        save_logs(logs)
    except Exception as e:
        logger.error(f"{PREFIX} push_log error: {e}")

class _SafeDict(dict):
    def __missing__(self, key):
        return ""

def _render_template(tpl: str, mapping: dict) -> str:
    tpl = (tpl or "").strip()
    if not tpl:
        tpl = _default_cfg()["template"]
    try:
        return tpl.format_map(_SafeDict(mapping))
    except Exception:
        return _default_cfg()["template"].format_map(_SafeDict(mapping))

def generate_steam_guard_code(shared_secret: str) -> Optional[str]:
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
        logger.error(f"{PREFIX} generate code error: {e}")
        return None

def _mid(msg) -> int:
    return int(getattr(msg, "message_id", None) or getattr(msg, "id", 0) or 0)

def _safe_edit(bot, chat_id: int, msg_id: int, text: str, kb: Optional[InlineKeyboardMarkup] = None):
    try:
        bot.edit_message_text(
            text,
            chat_id,
            msg_id,
            parse_mode="HTML",
            reply_markup=kb,
            disable_web_page_preview=True
        )
    except ApiTelegramException as e:
        if "message is not modified" in str(e).lower():
            return
        raise

def _try_delete(bot, chat_id: int, msg_id: int):
    try:
        bot.delete_message(chat_id, msg_id)
    except Exception:
        pass

def _answer_cbq(bot, call, text: Optional[str] = None, alert: bool = False):
    try:
        if text is None:
            bot.answer_callback_query(call.id)
        else:
            bot.answer_callback_query(call.id, text, show_alert=alert)
    except Exception:
        pass

def _cancel_kb(back_cb: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("❌ Отменить", callback_data=CB_CANCEL),
        InlineKeyboardButton("◀️ Назад", callback_data=back_cb),
    )
    return kb

def _welcome_text() -> str:
    return (
        f"🧩 <b>Плагин:</b> <b>{NAME}</b>\n"
        f"📦 Версия: <code>{escape(VERSION)}</code>\n"
        f"👤 Создатель: <code>{escape(CREDITS)}</code>"
    )

def _welcome_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("⚙️ Настройки", callback_data=CB_SETTINGS),
        InlineKeyboardButton("📘 Инструкция", url=INSTRUCTION_URL),
    )
    kb.row(InlineKeyboardButton("🗑 Удалить плагин", callback_data=CB_DELETE_PLUGIN))
    kb.row(InlineKeyboardButton("🔙 К списку плагинов", callback_data=CBT_PLUGINS_LIST_OPEN))
    return kb

def open_welcome(cardinal: "Cardinal", call_or_msg):
    bot = cardinal.telegram.bot
    text = _welcome_text()
    kb = _welcome_kb()

    if hasattr(call_or_msg, "message"):
        _answer_cbq(bot, call_or_msg)
        chat_id = call_or_msg.message.chat.id
        msg_id = _mid(call_or_msg.message)
        _safe_edit(bot, chat_id, msg_id, text, kb)
    else:
        chat_id = call_or_msg.chat.id
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)

def _settings_text(chat_id: int) -> str:
    data = load_data()
    cfg = _get_cfg(data)
    accounts = _get_accounts_for(chat_id, data)

    tpl = (cfg.get("template") or "").strip()
    tpl_short = (tpl[:120] + "…") if len(tpl) > 120 else (tpl or "—")

    return (
        "⚙️ <b>Настройки</b>\n\n"
        f"Аккаунтов: <b>{len(accounts)}</b>\n"
        f"Шаблон ответа:\n<code>{escape(tpl_short)}</code>\n\n"
        "Выбери действие:"
    )

def _settings_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("➕ Добавить аккаунт", callback_data=CB_ADD),
        InlineKeyboardButton("📜 Список аккаунтов", callback_data=CB_LIST),
    )
    kb.row(
        InlineKeyboardButton("🗑 Удалить аккаунт", callback_data=CB_DEL_MENU),
        InlineKeyboardButton("🧾 Логи", callback_data=f"{CB_LOGS}:0"),
    )
    kb.row(InlineKeyboardButton("✏️ Сообщение выдачи кода", callback_data=CB_TEMPLATE))
    kb.row(InlineKeyboardButton("◀️ Назад", callback_data=CB_WELCOME))
    return kb

def open_settings(cardinal: "Cardinal", call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    _safe_edit(bot, chat_id, msg_id, _settings_text(chat_id), _settings_kb())

def _list_text(chat_id: int) -> str:
    data = load_data()
    accounts = _get_accounts_for(chat_id, data)
    if not accounts:
        return "📜 <b>Список аккаунтов</b>\n\n❌ Аккаунтов нет."
    lines = []
    for i, acc in enumerate(accounts, start=1):
        shown_cmd = _normalize_cmd(str(acc.get("command", "")))
        lines.append(
            f"{i}) 🏷 <b>{escape(str(acc.get('name','')))}</b>\n"
            f"   💬 <code>{escape(shown_cmd)}</code>\n"
            f"   🔢 <code>{escape(_limit_text(acc))}</code>"
        )
    return "📜 <b>Список аккаунтов</b>\n\n" + "\n\n".join(lines)

def _back_to_settings_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("◀️ Назад", callback_data=CB_SETTINGS))
    return kb

def open_list(cardinal: "Cardinal", call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    _safe_edit(bot, chat_id, msg_id, _list_text(chat_id), _back_to_settings_kb())

def _del_menu_text(chat_id: int) -> str:
    data = load_data()
    accounts = _get_accounts_for(chat_id, data)
    if not accounts:
        return "🗑 <b>Удалить аккаунт</b>\n\n❌ Аккаунтов нет."
    return "🗑 <b>Удалить аккаунт</b>\n\nВыбери аккаунт для удаления:"

def _del_menu_kb(chat_id: int) -> InlineKeyboardMarkup:
    data = load_data()
    accounts = _get_accounts_for(chat_id, data)
    kb = InlineKeyboardMarkup()
    for idx, acc in enumerate(accounts):
        title = str(acc.get("name") or f"Аккаунт {idx+1}")
        cmd = _normalize_cmd(str(acc.get("command") or ""))
        kb.row(InlineKeyboardButton(f"🗑 {title} ({cmd})", callback_data=f"{CB_DEL_PICK}:{idx}"))
    kb.row(InlineKeyboardButton("◀️ Назад", callback_data=CB_SETTINGS))
    return kb

def open_del_menu(cardinal: "Cardinal", call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    _safe_edit(bot, chat_id, msg_id, _del_menu_text(chat_id), _del_menu_kb(chat_id))

def _del_confirm_text(acc: dict) -> str:
    return (
        "🗑 <b>Подтверждение удаления</b>\n\n"
        f"Удалить аккаунт:\n"
        f"🏷 <b>{escape(str(acc.get('name','')))}</b>\n"
        f"💬 <code>{escape(_normalize_cmd(str(acc.get('command',''))))}</code>\n\n"
        "Это действие необратимо."
    )

def _del_confirm_kb(idx: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("✅ Да", callback_data=f"{CB_DEL_YES}:{idx}"),
        InlineKeyboardButton("❌ Нет", callback_data=CB_DEL_NO),
    )
    kb.row(InlineKeyboardButton("◀️ Назад", callback_data=CB_DEL_MENU))
    return kb

def open_del_confirm(cardinal: "Cardinal", call, idx: int):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)

    data = load_data()
    accounts = _get_accounts_for(chat_id, data)
    if idx < 0 or idx >= len(accounts):
        _safe_edit(bot, chat_id, msg_id, "❌ Аккаунт не найден.", _back_to_settings_kb())
        return

    _safe_edit(bot, chat_id, msg_id, _del_confirm_text(accounts[idx]), _del_confirm_kb(idx))

def del_yes(cardinal: "Cardinal", call, idx: int):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)

    data = load_data()
    accounts = _get_accounts_for(chat_id, data)
    if idx < 0 or idx >= len(accounts):
        _safe_edit(bot, chat_id, msg_id, "❌ Аккаунт не найден.", _back_to_settings_kb())
        return

    removed = accounts.pop(idx)
    _set_accounts_for(chat_id, data, accounts)
    _get_cfg(data)
    save_data(data)

    _safe_edit(
        bot,
        chat_id,
        msg_id,
        f"✅ Аккаунт удалён: <b>{escape(str(removed.get('name','')))}</b>",
        _settings_kb()
    )

def del_no(cardinal: "Cardinal", call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call, "Отменено.")
    open_del_menu(cardinal, call)

def _logs_text(chat_id: int, page: int = 0, per_page: int = 12) -> str:
    owner_uid = str(chat_id)
    logs = load_logs()
    arr = logs.get(owner_uid)
    if not isinstance(arr, list) or not arr:
        return "🧾 <b>Логи</b>\n\n❌ Пока пусто."

    arr = arr[:]
    arr.reverse()

    page = max(0, int(page))
    start = page * per_page
    end = start + per_page
    chunk = arr[start:end]

    lines = []
    for e in chunk:
        ts = int(e.get("ts") or 0)
        kind = str(e.get("type") or "")
        cmd = str(e.get("cmd") or "")
        buyer = str(e.get("buyer") or "")
        name = str(e.get("name") or "")
        msg = str(e.get("msg") or "")
        lines.append(
            f"• <code>{escape(_fmt_dt(ts))}</code>\n"
            f"  <b>{escape(kind)}</b> | {escape(name)} | <code>{escape(cmd)}</code>\n"
            f"  buyer: <code>{escape(buyer)}</code>\n"
            f"  {escape(msg)}"
        )

    total_pages = (len(arr) + per_page - 1) // per_page
    return (
        "🧾 <b>Логи</b>\n\n"
        + "\n\n".join(lines)
        + f"\n\nСтраница: <b>{page+1}/{max(1, total_pages)}</b>"
    )

def _logs_kb(chat_id: int, page: int, per_page: int = 12) -> InlineKeyboardMarkup:
    owner_uid = str(chat_id)
    logs = load_logs()
    arr = logs.get(owner_uid)
    total = len(arr) if isinstance(arr, list) else 0
    total_pages = (total + per_page - 1) // per_page
    total_pages = max(1, total_pages)
    page = max(0, min(int(page), total_pages - 1))
    prev_page = max(0, page - 1)
    next_page = min(total_pages - 1, page + 1)

    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("⬅️ Назад", callback_data=f"{CB_LOGS}:{prev_page}"),
        InlineKeyboardButton("➡️ Вперёд", callback_data=f"{CB_LOGS}:{next_page}")
    )
    kb.row(InlineKeyboardButton("◀️ Назад в настройки", callback_data=CB_SETTINGS))
    return kb

def open_logs(cardinal: "Cardinal", call, page: int):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    _safe_edit(bot, chat_id, msg_id, _logs_text(chat_id, page), _logs_kb(chat_id, page))

def _template_text(chat_id: int) -> str:
    data = load_data()
    cfg = _get_cfg(data)
    tpl = (cfg.get("template") or "").strip()

    return (
        "✏️ <b>Сообщение выдачи кода</b>\n\n"
        "Текущий шаблон:\n"
        f"<code>{escape(tpl or '—')}</code>\n\n"
        "Плейсхолдеры:\n"
        "• <code>{code}</code> — код\n"
        "• <code>{name}</code> — название аккаунта\n"
        "• <code>{command}</code> — команда\n"
        "• <code>{left}</code> — осталось\n"
        "• <code>{total}</code> — всего/∞\n"
        "• <code>{limit_text}</code> — лимит текстом\n\n"
        "Отправь новый шаблон <b>одним сообщением</b>.\n"
        "⚠️ Сообщение будет удалено автоматически."
    )

def start_template_edit(cardinal: "Cardinal", call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)

    _fsm[chat_id] = {
        "mode": "template",
        "panel_chat_id": chat_id,
        "panel_msg_id": msg_id,
        "return": CB_SETTINGS
    }

    _safe_edit(bot, chat_id, msg_id, _template_text(chat_id), _cancel_kb(CB_SETTINGS))

def _fsm_cancel(cardinal: "Cardinal", call):
    bot = cardinal.telegram.bot
    chat_id = call.message.chat.id
    _fsm.pop(chat_id, None)
    _answer_cbq(bot, call, "Отменено.")
    open_settings(cardinal, call)

def _start_add(cardinal: "Cardinal", call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)

    _fsm[chat_id] = {
        "mode": "add",
        "step": "secret",
        "panel_chat_id": chat_id,
        "panel_msg_id": msg_id,
        "tmp": {},
        "return": CB_SETTINGS,
    }

    _safe_edit(
        bot,
        chat_id,
        msg_id,
        "➕ <b>Добавление SDA аккаунта</b>\n\n"
        "Шаг 1/5: отправь <b>shared_secret</b> одним сообщением.\n"
        "⚠️ Сообщение будет удалено автоматически.",
        _cancel_kb(CB_SETTINGS)
    )

def _restart_add(bot, chat_id: int, panel_msg_id: int):
    _fsm[chat_id] = {
        "mode": "add",
        "step": "secret",
        "panel_chat_id": chat_id,
        "panel_msg_id": panel_msg_id,
        "tmp": {},
        "return": CB_SETTINGS,
    }
    _safe_edit(
        bot, chat_id, panel_msg_id,
        "⚠️ Похоже, состояние добавления сбилось. Начнём заново.\n\n"
        "Шаг 1/5: отправь <b>shared_secret</b> одним сообщением.\n"
        "⚠️ Сообщение будет удалено автоматически.",
        _cancel_kb(CB_SETTINGS)
    )

def _handle_fsm(message: Message, cardinal: "Cardinal"):
    chat_id = message.chat.id
    if chat_id not in _fsm:
        return

    st = _fsm.get(chat_id) or {}
    mode = st.get("mode")
    bot = cardinal.telegram.bot

    panel_msg_id = int(st.get("panel_msg_id") or 0)
    text = (message.text or "").strip()

    _try_delete(bot, chat_id, _mid(message))

    if not text:
        return

    if text.startswith("/"):
        _fsm.pop(chat_id, None)
        if panel_msg_id:
            _safe_edit(bot, chat_id, panel_msg_id, "❌ Операция отменена.", _settings_kb())
        return

    if mode == "template":
        tpl = text.strip()
        data = load_data()
        cfg = _get_cfg(data)
        cfg["template"] = tpl
        _set_cfg(cfg)

        _fsm.pop(chat_id, None)
        if panel_msg_id:
            _safe_edit(bot, chat_id, panel_msg_id, "✅ Шаблон обновлён.", _settings_kb())
        return

    if mode != "add":
        return

    tmp = st.setdefault("tmp", {})
    step = st.get("step")

    if not panel_msg_id:
        return

    data = load_data()
    accounts = _get_accounts_for(chat_id, data)

    if step == "secret":
        shared_secret = text
        if not generate_steam_guard_code(shared_secret):
            _safe_edit(
                bot, chat_id, panel_msg_id,
                "❌ <b>Невалидный shared_secret</b>.\n\n"
                "Отправь shared_secret ещё раз одним сообщением.",
                _cancel_kb(CB_SETTINGS)
            )
            return

        tmp["shared_secret"] = shared_secret
        st["step"] = "name"
        _safe_edit(
            bot, chat_id, panel_msg_id,
            "Шаг 2/5: введи <b>название аккаунта</b> (например: Main).",
            _cancel_kb(CB_SETTINGS)
        )
        return

    if step == "name":
        tmp["name"] = text
        st["step"] = "command"
        _safe_edit(
            bot, chat_id, panel_msg_id,
            "Шаг 3/5: введи <b>команду</b> (пример: <code>!steam</code>).\n"
            "⚠️ Команда будет очищена от невидимых символов.",
            _cancel_kb(CB_SETTINGS)
        )
        return

    if step == "command":
        raw_cmd = text
        cmd = _normalize_cmd(raw_cmd)

        if not cmd:
            _safe_edit(bot, chat_id, panel_msg_id, "❌ Команда пустая. Введи ещё раз.", _cancel_kb(CB_SETTINGS))
            return

        reserved = {"sda_menu", "/sda_menu"}
        if cmd in reserved or cmd.lstrip("/") in reserved:
            _safe_edit(bot, chat_id, panel_msg_id, "❌ Команда зарезервирована. Введи другую.", _cancel_kb(CB_SETTINGS))
            return

        if any(_normalize_cmd(str(a.get("command", ""))) == cmd for a in accounts):
            _safe_edit(bot, chat_id, panel_msg_id, "❌ Такая команда уже существует. Введи другую.", _cancel_kb(CB_SETTINGS))
            return

        tmp["command"] = cmd
        st["step"] = "limit"
        _safe_edit(
            bot, chat_id, panel_msg_id,
            "Шаг 4/5: введи <b>лимит</b>.\n\n"
            "ℹ️ <b>Лимит</b> — сколько раз один покупатель может запросить код по команде.\n"
            "Примеры:\n"
            "• <code>5</code> — 5 запросов на покупателя\n"
            "• <code>-</code> — безлимит",
            _cancel_kb(CB_SETTINGS)
        )
        return

    if step == "limit":
        if "name" not in tmp or "command" not in tmp or "shared_secret" not in tmp:
            _restart_add(bot, chat_id, panel_msg_id)
            return

        raw = text.strip()
        if raw == "-":
            acc = {
                "name": tmp["name"],
                "command": tmp["command"],
                "shared_secret": tmp["shared_secret"],
                "limit": None,
                "period_hours": None
            }
            accounts.append(acc)
            _set_accounts_for(chat_id, data, accounts)
            _get_cfg(data)
            save_data(data)

            _fsm.pop(chat_id, None)
            _safe_edit(
                bot, chat_id, panel_msg_id,
                "✅ <b>Аккаунт добавлен</b>\n\n"
                f"🏷 <b>{escape(acc['name'])}</b>\n"
                f"💬 <code>{escape(acc['command'])}</code>\n"
                f"🔢 <code>без ограничений</code>\n"
                f"🔐 secret: <code>{escape(_mask_secret(acc['shared_secret']))}</code>",
                _settings_kb()
            )
            return

        try:
            limit = int(raw)
            if limit <= 0:
                raise ValueError
        except ValueError:
            _safe_edit(bot, chat_id, panel_msg_id, "❌ Введи число > 0 или <code>-</code>.", _cancel_kb(CB_SETTINGS))
            return

        tmp["limit"] = limit
        st["step"] = "period"
        _safe_edit(
            bot, chat_id, panel_msg_id,
            "Шаг 5/5: введи <b>период в часах</b>.\n\n"
            "ℹ️ Если период = 24 — лимит обновится через 24 часа.\n"
            "ℹ️ Если период = <code>0</code> или <code>-</code> — лимит навсегда (на покупателя).\n\n"
            "Примеры: <code>24</code> / <code>0</code> / <code>-</code>",
            _cancel_kb(CB_SETTINGS)
        )
        return

    if step == "period":
        if "name" not in tmp or "command" not in tmp or "shared_secret" not in tmp or "limit" not in tmp:
            _restart_add(bot, chat_id, panel_msg_id)
            return

        raw = text.strip()
        limit = int(tmp["limit"])

        if raw in {"-", "0"}:
            acc = {
                "name": tmp["name"],
                "command": tmp["command"],
                "shared_secret": tmp["shared_secret"],
                "limit": limit,
                "period_hours": None
            }
            accounts.append(acc)
            _set_accounts_for(chat_id, data, accounts)
            _get_cfg(data)
            save_data(data)

            _fsm.pop(chat_id, None)
            _safe_edit(
                bot, chat_id, panel_msg_id,
                "✅ <b>Аккаунт добавлен</b>\n\n"
                f"🏷 <b>{escape(acc['name'])}</b>\n"
                f"💬 <code>{escape(acc['command'])}</code>\n"
                f"🔢 <code>{limit} навсегда</code>\n"
                f"🔐 secret: <code>{escape(_mask_secret(acc['shared_secret']))}</code>",
                _settings_kb()
            )
            return

        try:
            hours = int(raw)
            if hours <= 0:
                raise ValueError
        except ValueError:
            _safe_edit(bot, chat_id, panel_msg_id, "❌ Введи число > 0, либо <code>-</code> / <code>0</code>.", _cancel_kb(CB_SETTINGS))
            return

        acc = {
            "name": tmp["name"],
            "command": tmp["command"],
            "shared_secret": tmp["shared_secret"],
            "limit": limit,
            "period_hours": hours
        }
        accounts.append(acc)
        _set_accounts_for(chat_id, data, accounts)
        _get_cfg(data)
        save_data(data)

        _fsm.pop(chat_id, None)
        _safe_edit(
            bot, chat_id, panel_msg_id,
            "✅ <b>Аккаунт добавлен</b>\n\n"
            f"🏷 <b>{escape(acc['name'])}</b>\n"
            f"💬 <code>{escape(acc['command'])}</code>\n"
            f"🔢 <code>{limit} за {hours}ч</code>\n"
            f"🔐 secret: <code>{escape(_mask_secret(acc['shared_secret']))}</code>",
            _settings_kb()
        )
        return

    _restart_add(bot, chat_id, panel_msg_id)

def _delete_plugin_text() -> str:
    return (
        "🗑 <b>Удаление плагина</b>\n\n"
        f"Ты точно хочешь удалить <b>{escape(NAME)}</b>?\n"
        "Это действие может быть необратимым."
    )

def _delete_plugin_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("✅ Да, удалить", callback_data=CB_DELETE_PLUGIN_YES),
        InlineKeyboardButton("❌ Нет", callback_data=CB_DELETE_PLUGIN_NO),
    )
    kb.row(InlineKeyboardButton("◀️ Назад", callback_data=CB_WELCOME))
    return kb

def _delete_plugin_open(cardinal: "Cardinal", call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    _safe_edit(bot, call.message.chat.id, _mid(call.message), _delete_plugin_text(), _delete_plugin_kb())

def _delete_plugin_no(cardinal: "Cardinal", call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call, "Отменено.")
    open_welcome(cardinal, call)

def _delete_plugin_try(cardinal: "Cardinal", call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)

    ok = False
    err = None

    candidates = [
        (cardinal, "delete_plugin"),
        (cardinal, "remove_plugin"),
        (cardinal, "uninstall_plugin"),
        (cardinal, "unload_plugin"),
        (getattr(cardinal, "plugins", None), "delete_plugin"),
        (getattr(cardinal, "plugins", None), "remove_plugin"),
        (getattr(cardinal, "plugin_manager", None), "delete_plugin"),
        (getattr(cardinal, "plugin_manager", None), "remove_plugin"),
        (getattr(cardinal, "plugin_manager", None), "unload_plugin"),
    ]

    for obj, method in candidates:
        try:
            if obj is None:
                continue
            fn = getattr(obj, method, None)
            if callable(fn):
                fn(UUID)
                ok = True
                break
        except Exception as e:
            err = e

    if ok:
        try:
            bot.edit_message_text(
                "✅ Плагин удалён.\n\nЕсли он всё ещё виден в меню — перезапусти Cardinal.",
                call.message.chat.id,
                _mid(call.message),
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        except Exception:
            pass
        return

    _safe_edit(
        bot,
        call.message.chat.id,
        _mid(call.message),
        "❌ Не смог удалить плагин автоматически.\n\n"
        "Удаление вручную:\n"
        "1) Cardinal → Плагины\n"
        f"2) Найди <b>{escape(NAME)}</b>\n"
        "3) Нажми <b>Удалить</b>\n\n"
        f"Ошибка (если была): <code>{escape(str(err)) if err else '—'}</code>",
        _welcome_kb()
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
    m, s = divmod(max(0, int(seconds)), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}ч {m}м"
    if m:
        return f"{m}м"
    return f"{s}с"

def new_message_handler(cardinal: "Cardinal", event: NewMessageEvent):
    try:
        raw_text = _get_text_from_event_message(event.message)
        text = _normalize_cmd(raw_text)
        if not text:
            return

        buyer_id = _get_buyer_id_from_event_message(event.message)
        now = int(time.time())

        data = load_data()
        cfg = _get_cfg(data)
        tpl = str(cfg.get("template") or _default_cfg()["template"])

        usage = load_usage()

        for owner_uid, accounts in (data or {}).items():
            if owner_uid == "global" or not isinstance(accounts, list):
                continue

            for acc in accounts:
                cmd_raw = str(acc.get("command", "") or "")
                cmd = _normalize_cmd(cmd_raw)
                if not cmd or text != cmd:
                    continue

                name = str(acc.get("name", "") or "")
                shared = str(acc.get("shared_secret", "") or "")
                limit = acc.get("limit")
                period_hours = acc.get("period_hours")

                if limit is None:
                    code = generate_steam_guard_code(shared)
                    if code:
                        msg = _render_template(tpl, {
                            "code": code,
                            "name": name,
                            "command": cmd,
                            "left": "∞",
                            "total": "∞",
                            "limit_text": _limit_text(acc),
                        })
                        cardinal.account.send_message(event.message.chat_id, msg)
                        _push_log(owner_uid, {"ts": now, "type": "CODE", "name": name, "cmd": cmd, "buyer": buyer_id, "msg": "выдан (безлимит)"})
                    else:
                        cardinal.account.send_message(event.message.chat_id, "❌ Ошибка генерации.")
                        _push_log(owner_uid, {"ts": now, "type": "ERROR", "name": name, "cmd": cmd, "buyer": buyer_id, "msg": "ошибка генерации (безлимит)"})
                    return
                limit = int(limit)
                usage.setdefault(owner_uid, {}).setdefault(buyer_id, {})
                old_key = str(acc.get("command", "") or "").lower().strip()
                if old_key and old_key != cmd and old_key in usage[owner_uid][buyer_id] and cmd not in usage[owner_uid][buyer_id]:
                    usage[owner_uid][buyer_id][cmd] = usage[owner_uid][buyer_id].pop(old_key)

                usage[owner_uid][buyer_id].setdefault(cmd, {"count": 0})
                record = usage[owner_uid][buyer_id][cmd]

                if period_hours is None:
                    if int(record["count"]) >= limit:
                        cardinal.account.send_message(event.message.chat_id, f"❌ Лимит {limit} навсегда исчерпан.")
                        save_usage(usage)
                        _push_log(owner_uid, {"ts": now, "type": "LIMIT", "name": name, "cmd": cmd, "buyer": buyer_id, "msg": f"лимит навсегда исчерпан ({limit})"})
                        return
                else:
                    period_seconds = int(period_hours) * 3600
                    record.setdefault("reset_time", now + period_seconds)
                    if now > int(record["reset_time"]):
                        record["count"] = 0
                        record["reset_time"] = now + period_seconds

                    if int(record["count"]) >= limit:
                        seconds_left = int(record["reset_time"] - now)
                        cardinal.account.send_message(event.message.chat_id, f"❌ Лимит исчерпан. Новый запрос через {_format_time_left(seconds_left)}.")
                        save_usage(usage)
                        _push_log(owner_uid, {"ts": now, "type": "LIMIT", "name": name, "cmd": cmd, "buyer": buyer_id, "msg": f"лимит исчерпан, ждать {seconds_left}s"})
                        return

                code = generate_steam_guard_code(shared)
                if not code:
                    cardinal.account.send_message(event.message.chat_id, "❌ Ошибка генерации.")
                    _push_log(owner_uid, {"ts": now, "type": "ERROR", "name": name, "cmd": cmd, "buyer": buyer_id, "msg": "ошибка генерации"})
                    return

                record["count"] = int(record.get("count") or 0) + 1
                save_usage(usage)

                left = max(0, limit - int(record["count"]))
                total = "∞" if period_hours is None else str(limit)

                msg = _render_template(tpl, {
                    "code": code,
                    "name": name,
                    "command": cmd,
                    "left": str(left),
                    "total": str(total),
                    "limit_text": _limit_text(acc),
                })
                cardinal.account.send_message(event.message.chat_id, msg)
                _push_log(owner_uid, {"ts": now, "type": "CODE", "name": name, "cmd": cmd, "buyer": buyer_id, "msg": f"выдан, осталось {left}/{total}"})
                return

    except Exception as e:
        logger.exception(f"{PREFIX} new_message_handler error: {e}")

def init_cardinal(cardinal: "Cardinal"):
    tg = cardinal.telegram

    tg.msg_handler(lambda m: open_welcome(cardinal, m), commands=["sda_menu"])
    tg.msg_handler(lambda m: _handle_fsm(m, cardinal), func=lambda m: m.chat.id in _fsm)

    tg.cbq_handler(
        lambda c: open_welcome(cardinal, c),
        func=lambda c:
            c.data.startswith(f"{CBT_EDIT_PLUGIN}:{UUID}")
            or c.data.startswith(f"{CBT_PLUGIN_SETTINGS}:{UUID}")
            or c.data == CB_WELCOME
    )

    tg.cbq_handler(lambda c: open_settings(cardinal, c), func=lambda c: c.data == CB_SETTINGS)
    tg.cbq_handler(lambda c: _start_add(cardinal, c), func=lambda c: c.data == CB_ADD)
    tg.cbq_handler(lambda c: open_list(cardinal, c), func=lambda c: c.data == CB_LIST)
    tg.cbq_handler(lambda c: open_del_menu(cardinal, c), func=lambda c: c.data == CB_DEL_MENU)
    tg.cbq_handler(lambda c: start_template_edit(cardinal, c), func=lambda c: c.data == CB_TEMPLATE)
    tg.cbq_handler(lambda c: _fsm_cancel(cardinal, c), func=lambda c: c.data == CB_CANCEL)

    tg.cbq_handler(
        lambda c: open_del_confirm(cardinal, c, int(c.data.split(":")[-1])),
        func=lambda c: c.data.startswith(f"{CB_DEL_PICK}:")
    )
    tg.cbq_handler(
        lambda c: del_yes(cardinal, c, int(c.data.split(":")[-1])),
        func=lambda c: c.data.startswith(f"{CB_DEL_YES}:")
    )
    tg.cbq_handler(lambda c: del_no(cardinal, c), func=lambda c: c.data == CB_DEL_NO)

    tg.cbq_handler(
        lambda c: open_logs(cardinal, c, int(c.data.split(":")[-1])),
        func=lambda c: c.data.startswith(f"{CB_LOGS}:")
    )

    tg.cbq_handler(lambda c: _delete_plugin_open(cardinal, c), func=lambda c: c.data == CB_DELETE_PLUGIN)
    tg.cbq_handler(lambda c: _delete_plugin_try(cardinal, c), func=lambda c: c.data == CB_DELETE_PLUGIN_YES)
    tg.cbq_handler(lambda c: _delete_plugin_no(cardinal, c), func=lambda c: c.data == CB_DELETE_PLUGIN_NO)

    tg.cbq_handler(lambda c: open_welcome(cardinal, c), func=lambda c: c.data == CB_WELCOME)
    tg.cbq_handler(lambda c: open_welcome(cardinal, c), func=lambda c: c.data == CBT_BACK)

    try:
        cardinal.add_telegram_commands(UUID, [
            ("sda_menu", "Открыть меню Steam Guard (SDA)", True),
        ])
    except Exception as e:
        logger.warning(f"{PREFIX} add_telegram_commands failed: {e}")

BIND_TO_PRE_INIT = [init_cardinal]
BIND_TO_NEW_MESSAGE = [new_message_handler]
BIND_TO_DELETE = None
