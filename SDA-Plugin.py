from __future__ import annotations
from typing import TYPE_CHECKING, Dict, Any, Optional, List
import os
import json
import base64
import hmac
import hashlib
import time
import logging
import re
import unicodedata
import threading
import io
import shutil
from html import escape, unescape
from datetime import datetime
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from telebot.apihelper import ApiTelegramException
from FunPayAPI.updater.events import NewMessageEvent
if TYPE_CHECKING:
    from cardinal import Cardinal
NAME = 'Steam Guard (SDA)'
VERSION = '1.4'
DESCRIPTION = 'Получение Steam Guard (SDA) кода по команде.'
CREDITS = '@tinechelovec'
UUID = 'b886288e-7908-4f62-bd48-48e1a5c7a8e5'
SETTINGS_PAGE = True
logger = logging.getLogger('SteamGuardSDA')
PREFIX = '[SteamGuardSDA]'
INSTRUCTION_URL = f'https://teletype.in/@tinechelovec/Steam-Guard-SDA'
CREATOR_URL = 'https://t.me/tinechelovec'
GROUP_URL = 'https://t.me/dev_thc_chat'
CHANNEL_URL = 'https://t.me/by_thc'
SDA_GITHUB_URL = os.getenv('SDA_PLUGIN_GITHUB_URL', 'https://github.com/tinechelovec/FPC-Plugin-Steam-Guard-SDA').strip()
SDA_UPDATE_URL = os.getenv('SDA_PLUGIN_UPDATE_URL', 'https://raw.githubusercontent.com/tinechelovec/FPC-Plugin-Steam-Guard-SDA/main/SDA-Plugin.py').strip()
PLUGIN_FOLDER = 'storage/plugins/steam_guard_sda'
DATA_FILE = os.path.join(PLUGIN_FOLDER, 'data.json')
USAGE_FILE = os.path.join(PLUGIN_FOLDER, 'usage.json')
LOGS_FILE = os.path.join(PLUGIN_FOLDER, 'logs.json')
QUEUE_FILE = os.path.join(PLUGIN_FOLDER, 'queue.json')
NOTIFY_DEBUG_FILE = os.path.join(PLUGIN_FOLDER, 'notify_debug.log')
os.makedirs(PLUGIN_FOLDER, exist_ok=True)
for fpath, default in [(DATA_FILE, {}), (USAGE_FILE, {}), (LOGS_FILE, {}), (QUEUE_FILE, {})]:
    if not os.path.exists(fpath):
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(default, f, indent=4, ensure_ascii=False)
try:
    import tg_bot.CBT as CBT
except Exception:

    class CBT:
        EDIT_PLUGIN = 'PLUGIN_EDIT'
        PLUGIN_SETTINGS = 'PLUGIN_SETTINGS'
        PLUGINS_LIST = '44'
        BACK = None
CBT_EDIT_PLUGIN = getattr(CBT, 'EDIT_PLUGIN', 'PLUGIN_EDIT')
CBT_PLUGIN_SETTINGS = getattr(CBT, 'PLUGIN_SETTINGS', 'PLUGIN_SETTINGS')
CBT_PLUGINS_LIST_OPEN = f"{getattr(CBT, 'PLUGINS_LIST', '44')}:0"
CBT_BACK = getattr(CBT, 'BACK', None) or f'{UUID}:back'
CB_WELCOME = f'{UUID}:welcome'
CB_INFO = f'{UUID}:info'
CB_SETTINGS = f'{UUID}:settings'
CB_INSTRUCTION_ACK = f'{UUID}:instruction_ack'
CB_UPDATE_PLUGIN = f'{UUID}:update_plugin'
CB_UPDATE_PLUGIN_LOCAL = f'{UUID}:update_plugin_local'
CB_UPDATE_PLUGIN_ONLINE = f'{UUID}:update_plugin_online'
CB_UPDATE_PLUGIN_YES = f'{UUID}:update_plugin_yes'
CB_UPDATE_PLUGIN_NO = f'{UUID}:update_plugin_no'
CB_ADD = f'{UUID}:add'
CB_LIST = f'{UUID}:list'
CB_DEL_MENU = f'{UUID}:del_menu'
CB_DEL_PICK = f'{UUID}:del_pick'
CB_DEL_YES = f'{UUID}:del_yes'
CB_DEL_NO = f'{UUID}:del_no'
CB_LOGS = f'{UUID}:logs'
CB_TEMPLATE = f'{UUID}:template'
CB_TEMPLATE_MODE_TOGGLE = f'{UUID}:tpl_mode'
CB_ACCOUNT_TEMPLATE_MENU = f'{UUID}:acc_tpl_menu'
CB_ACCOUNT_TEMPLATE_PICK = f'{UUID}:acc_tpl_pick'
CB_CANCEL = f'{UUID}:cancel'
CB_ADD_CMD_AUTO = f'{UUID}:add_cmd_auto'
CB_ADD_CMD_CUSTOM = f'{UUID}:add_cmd_custom'
CB_ADD_TEMPLATE_GLOBAL = f'{UUID}:add_tpl_global'
CB_ADD_TEMPLATE_CUSTOM = f'{UUID}:add_tpl_custom'
CB_ADD_QUEUE_YES = f'{UUID}:add_queue_yes'
CB_ADD_QUEUE_NO = f'{UUID}:add_queue_no'
CB_CONFIG_MENU = f'{UUID}:config_menu'
CB_CONFIG_EXPORT = f'{UUID}:config_export'
CB_CONFIG_IMPORT = f'{UUID}:config_import'
CB_LIST_PAGE = f'{UUID}:lp'
CB_ACCOUNT_OPEN = f'{UUID}:ao'
CB_ACCOUNT_EDIT_COMMAND = f'{UUID}:ec'
CB_ACCOUNT_TEXT_MENU = f'{UUID}:et'
CB_ACCOUNT_TEXT_GLOBAL = f'{UUID}:eg'
CB_ACCOUNT_TEXT_CUSTOM = f'{UUID}:ex'
CB_ACCOUNT_EDIT_SECRET = f'{UUID}:es'
CB_ACCOUNT_EDIT_LIMIT = f'{UUID}:el'
CB_ACCOUNT_TOGGLE_ENABLED = f'{UUID}:ae'
CB_ACCOUNT_TOGGLE_QUEUE = f'{UUID}:aq'
CB_ACCOUNT_TOGGLE_NOTIFY = f'{UUID}:an'
CB_PLUGIN_TOGGLE = f'{UUID}:plugin_toggle'
CB_QUEUE_TOGGLE = f'{UUID}:queue_toggle'
CB_CMD_NOTIFY_TOGGLE = f'{UUID}:cmd_notify_toggle'
CB_CMD_NOTIFY_DEBUG_TOGGLE = f'{UUID}:cmd_notify_debug'
CB_BL = f'{UUID}:bl'
CB_BL_TOGGLE = f'{UUID}:bl_t'
CB_BL_SCOPE = f'{UUID}:bl_s'
CB_BL_NICKS = f'{UUID}:bl_n'
CB_BL_NICK_ADD = f'{UUID}:bl_na'
CB_BL_NICK_DEL = f'{UUID}:bl_nd'
CB_BL_NICK_PAGE = f'{UUID}:bl_np'
CB_BL_TEXT = f'{UUID}:bl_x'
CB_BL_ACCS = f'{UUID}:bl_a'
CB_BL_ACC_TOGGLE = f'{UUID}:bl_at'
CB_DELETE_PLUGIN = f'{UUID}:del_plugin'
CB_DELETE_PLUGIN_YES = f'{UUID}:del_plugin_yes'
CB_DELETE_PLUGIN_NO = f'{UUID}:del_plugin_no'
_fsm: Dict[int, Dict[str, Any]] = {}
_INVIS_RE = re.compile('[\\u200B-\\u200F\\u202A-\\u202E\\u2060-\\u206F\\uFE0E\\uFE0F\\u00AD]')
_usage_lock = threading.RLock()
_queue_lock = threading.RLock()
_timer_lock = threading.RLock()
_queue_timers: Dict[str, threading.Timer] = {}
_suppress_own_notification_until = 0.0
_suppress_own_notification_lock = threading.RLock()
_recent_command_suppressions: List[dict] = []
_notify_debug_lock = threading.RLock()
_logger_filter_lock = threading.RLock()
_original_logger_log = None
_logs_lock = threading.RLock()
_ui_audit_lock = threading.RLock()
_recent_ui_callback_ids: Dict[str, float] = {}

def _unwrap_callable_chain(func, max_depth: int=80):
    chain = []
    seen = set()
    cur = func
    for _ in range(max(1, int(max_depth))):
        if cur is None:
            break
        ident = id(cur)
        if ident in seen:
            chain.append(cur)
            break
        seen.add(ident)
        chain.append(cur)
        nxt = None
        for attr in ('_steam_guard_sda_original', '_ubisoft_totp_original'):
            candidate = getattr(cur, attr, None)
            if callable(candidate):
                nxt = candidate
                break
        if nxt is None:
            break
        cur = nxt
    return chain

def _callable_chain_has_attr(func, attr_name: str) -> bool:
    try:
        return any((bool(getattr(item, attr_name, False)) for item in _unwrap_callable_chain(func)))
    except Exception:
        return bool(getattr(func, attr_name, False))

def _normalize_cmd(s: str) -> str:
    if not s:
        return ''
    s = unicodedata.normalize('NFKC', str(s))
    s = s.replace('\xa0', ' ')
    s = _INVIS_RE.sub('', s)
    out = []
    for ch in s:
        cat = unicodedata.category(ch)
        if cat in ('Cc', 'Cf'):
            continue
        out.append(ch)
    s = ''.join(out)
    s = ''.join((ch for ch in s if not ch.isspace()))
    return s.strip().lower()

def _load_json(path: str) -> dict:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f'{PREFIX} _load_json({path}) error: {e}')
        return {}

def _save_json(path: str, data: dict):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f'{PREFIX} _save_json({path}) error: {e}')

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

def load_queue() -> dict:
    return _load_json(QUEUE_FILE)

def save_queue(data: dict):
    _save_json(QUEUE_FILE, data)

def _default_cfg() -> dict:
    return {'template': '✅ Ваш код: {code}\n📊 Осталось: {left}/{total}', 'template_mode': 'global', 'max_logs': 1000, 'plugin_enabled': True, 'queue_enabled': True, 'command_notifications_enabled': True, 'command_notifications_debug_enabled': True, 'instruction_acknowledged_chat_ids': [], 'blacklist_enabled': False, 'blacklist_scope': 'all', 'blacklist_nicks': [], 'blacklist_account_ids': [], 'blacklist_text': '⛔ Вы находитесь в чёрном списке.\nВыдача Steam Guard кода для аккаунта «{name}» недоступна.'}

def _get_cfg(data: dict) -> dict:
    g = data.get('global')
    base = _default_cfg()
    if isinstance(g, dict):
        base.update(g)
    if str(base.get('template_mode') or 'global') not in {'global', 'custom'}:
        base['template_mode'] = 'global'
    if str(base.get('blacklist_scope') or 'all') not in {'all', 'selected'}:
        base['blacklist_scope'] = 'all'
    if not isinstance(base.get('blacklist_nicks'), list):
        base['blacklist_nicks'] = []
    base['blacklist_nicks'] = [str(x).strip() for x in base.get('blacklist_nicks', []) if str(x or '').strip()]
    if not isinstance(base.get('blacklist_account_ids'), list):
        base['blacklist_account_ids'] = []
    base['blacklist_account_ids'] = [str(x).strip() for x in base.get('blacklist_account_ids', []) if str(x or '').strip()]
    if not isinstance(base.get('instruction_acknowledged_chat_ids'), list):
        base['instruction_acknowledged_chat_ids'] = []
    base['instruction_acknowledged_chat_ids'] = [str(x).strip() for x in base.get('instruction_acknowledged_chat_ids', []) if str(x or '').strip()]
    if not str(base.get('blacklist_text') or '').strip():
        base['blacklist_text'] = _default_cfg()['blacklist_text']
    data['global'] = base
    return data['global']

def _set_cfg(cfg: dict):
    data = load_data()
    data['global'] = cfg
    save_data(data)

def _plugin_enabled() -> bool:
    data = load_data()
    cfg = _get_cfg(data)
    return bool(cfg.get('plugin_enabled', True))

def _toggle_plugin_enabled() -> bool:
    data = load_data()
    cfg = _get_cfg(data)
    cfg['plugin_enabled'] = not bool(cfg.get('plugin_enabled', True))
    data['global'] = cfg
    save_data(data)
    return bool(cfg['plugin_enabled'])

def _queue_enabled() -> bool:
    data = load_data()
    cfg = _get_cfg(data)
    return bool(cfg.get('queue_enabled', True))

def _toggle_queue_enabled() -> bool:
    data = load_data()
    cfg = _get_cfg(data)
    cfg['queue_enabled'] = not bool(cfg.get('queue_enabled', True))
    data['global'] = cfg
    save_data(data)
    return bool(cfg['queue_enabled'])

def _command_notifications_enabled() -> bool:
    data = load_data()
    cfg = _get_cfg(data)
    return bool(cfg.get('command_notifications_enabled', True))

def _toggle_command_notifications_enabled() -> bool:
    data = load_data()
    cfg = _get_cfg(data)
    cfg['command_notifications_enabled'] = not bool(cfg.get('command_notifications_enabled', True))
    data['global'] = cfg
    save_data(data)
    return bool(cfg['command_notifications_enabled'])

def _command_notifications_debug_enabled() -> bool:
    data = load_data()
    cfg = _get_cfg(data)
    return bool(cfg.get('command_notifications_debug_enabled', True))

def _toggle_command_notifications_debug_enabled() -> bool:
    data = load_data()
    cfg = _get_cfg(data)
    cfg['command_notifications_debug_enabled'] = not bool(cfg.get('command_notifications_debug_enabled', True))
    data['global'] = cfg
    save_data(data)
    return bool(cfg['command_notifications_debug_enabled'])

def _template_mode() -> str:
    data = load_data()
    cfg = _get_cfg(data)
    mode = str(cfg.get('template_mode') or 'global')
    return mode if mode in {'global', 'custom'} else 'global'

def _template_mode_label(mode: Optional[str]=None) -> str:
    mode = str(mode or _template_mode())
    return 'Кастомный' if mode == 'custom' else 'Общий'

def _toggle_template_mode() -> str:
    data = load_data()
    cfg = _get_cfg(data)
    cfg['template_mode'] = 'custom' if str(cfg.get('template_mode') or 'global') == 'global' else 'global'
    data['global'] = cfg
    save_data(data)
    return str(cfg['template_mode'])

def _make_account_id(owner_uid: str, acc: dict, idx: int=0, salt: str='') -> str:
    raw = '|'.join([str(owner_uid), str(idx), _normalize_cmd(str(acc.get('command') or '')), str(acc.get('name') or ''), str(acc.get('shared_secret') or ''), str(salt)])
    return hashlib.sha1(raw.encode('utf-8', 'ignore')).hexdigest()[:10]

def _ensure_account_ids(owner_uid: str, accounts: List[dict]) -> bool:
    changed = False
    seen = set()
    for idx, acc in enumerate(accounts):
        if not isinstance(acc, dict):
            continue
        acc_id = str(acc.get('account_id') or '').strip()
        if not re.fullmatch('[a-f0-9]{10}', acc_id) or acc_id in seen:
            salt = 0
            acc_id = _make_account_id(owner_uid, acc, idx, str(salt))
            while acc_id in seen:
                salt += 1
                acc_id = _make_account_id(owner_uid, acc, idx, str(salt))
            acc['account_id'] = acc_id
            changed = True
        if 'template' not in acc:
            acc['template'] = ''
            changed = True
        if 'enabled' not in acc:
            acc['enabled'] = True
            changed = True
        if 'queue_enabled' not in acc:
            acc['queue_enabled'] = True
            changed = True
        if 'command_notifications_enabled' not in acc:
            acc['command_notifications_enabled'] = True
            changed = True
        seen.add(str(acc.get('account_id') or acc_id))
    return changed

def _get_accounts_for(chat_id: int, data: dict) -> List[dict]:
    uid = str(chat_id)
    arr = data.get(uid)
    if isinstance(arr, list):
        _ensure_account_ids(uid, arr)
        return arr
    return []

def _set_accounts_for(chat_id: int, data: dict, accounts: List[dict]):
    uid = str(chat_id)
    _ensure_account_ids(uid, accounts)
    data[uid] = accounts

def _find_account_index(accounts: List[dict], account_id: str) -> int:
    account_id = str(account_id or '').strip()
    for idx, acc in enumerate(accounts):
        if str(acc.get('account_id') or '').strip() == account_id:
            return idx
    return -1

def _limit_text(acc: dict) -> str:
    if acc.get('limit') is None:
        return 'без ограничений'
    if acc.get('period_hours') is None:
        return f"{acc['limit']} навсегда"
    return f"{acc['limit']} за {acc['period_hours']}ч"

def _mask_secret(s: str) -> str:
    if not s:
        return '—'
    t = s.strip()
    if len(t) <= 10:
        return '********'
    return t[:4] + '…' + t[-4:]

def _fmt_dt(ts: int) -> str:
    try:
        return datetime.fromtimestamp(int(ts)).strftime('%d.%m.%Y %H:%M:%S')
    except Exception:
        return str(ts)

def _push_log(owner_uid: str, entry: dict):
    try:
        owner_uid = str(owner_uid or '').strip()
        if not owner_uid:
            return
        clean = dict(entry or {})
        clean.setdefault('ts', int(time.time()))
        clean.setdefault('type', 'INFO')
        clean.setdefault('msg', '')
        for key, value in list(clean.items()):
            if value is None:
                clean[key] = ''
            elif not isinstance(value, (str, int, float, bool)):
                clean[key] = str(value)
            if isinstance(clean[key], str) and len(clean[key]) > 1500:
                clean[key] = clean[key][:1497] + '…'
        with _logs_lock:
            logs = load_logs()
            arr = logs.get(owner_uid)
            if not isinstance(arr, list):
                arr = []
            arr.append(clean)
            data = load_data()
            cfg = _get_cfg(data)
            try:
                max_logs = int(cfg.get('max_logs') or 1000)
            except (TypeError, ValueError):
                max_logs = 1000
            max_logs = max(500, min(max_logs, 5000))
            if len(arr) > max_logs:
                arr = arr[-max_logs:]
            logs[owner_uid] = arr
            save_logs(logs)
    except Exception as e:
        logger.error(f'{PREFIX} push_log error: {e}')

def _log_event(owner_uid: str, event_type: str, message: str, **details):
    entry = {'ts': int(time.time()), 'type': str(event_type or 'INFO').upper(), 'msg': str(message or '')}
    for key, value in details.items():
        if value not in (None, ''):
            entry[str(key)] = value
    _push_log(str(owner_uid), entry)

def _log_error_for_all_owners(where: str, error: Exception):
    try:
        data = load_data()
        for owner_uid, accounts in (data or {}).items():
            if owner_uid == 'global' or not isinstance(accounts, list):
                continue
            _log_event(str(owner_uid), 'ERROR', f'Ошибка в {where}: {type(error).__name__}: {error}', where=where)
    except Exception:
        pass

class _SafeDict(dict):

    def __missing__(self, key):
        return ''

def _render_template(tpl: str, mapping: dict) -> str:
    tpl = (tpl or '').strip()
    if not tpl:
        tpl = _default_cfg()['template']
    try:
        return tpl.format_map(_SafeDict(mapping))
    except Exception:
        return _default_cfg()['template'].format_map(_SafeDict(mapping))

def _get_template_by_mode(account_template: str, cfg: dict) -> str:
    global_tpl = str(cfg.get('template') or _default_cfg()['template'])
    acc_tpl = str(account_template or '').strip()
    return acc_tpl or global_tpl

def _get_account_template(acc: dict, cfg: dict) -> str:
    return _get_template_by_mode(str(acc.get('template') or ''), cfg)

def _normalize_nick(s: str) -> str:
    if not s:
        return ''
    s = unicodedata.normalize('NFKC', str(s))
    s = s.replace('\xa0', ' ')
    s = _INVIS_RE.sub('', s)
    s = re.sub('\\s+', ' ', s).strip()
    if s.startswith('@'):
        s = s[1:].strip()
    return s.casefold()

def _parse_blacklist_nicks(raw: str) -> List[str]:
    result = []
    seen = set()
    for part in re.split('[\\n,;]+', raw or ''):
        nick = part.strip()
        if nick.startswith('@'):
            nick = nick[1:].strip()
        norm = _normalize_nick(nick)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        result.append(nick)
    return result

def _blacklist_match(cfg: dict, buyer_nick: str) -> Optional[str]:
    buyer_norm = _normalize_nick(buyer_nick)
    if not buyer_norm:
        return None
    for nick in cfg.get('blacklist_nicks') or []:
        if _normalize_nick(str(nick)) == buyer_norm:
            return str(nick)
    return None

def _blacklist_scope_label(scope: Optional[str]=None) -> str:
    scope = str(scope or 'all')
    return 'выбранные аккаунты' if scope == 'selected' else 'все аккаунты'

def _blacklist_applies_to_account(owner_uid: str, acc: dict, cfg: dict) -> bool:
    if not bool(cfg.get('blacklist_enabled', False)):
        return False
    scope = str(cfg.get('blacklist_scope') or 'all')
    if scope == 'all':
        return True
    selected = set((str(x) for x in cfg.get('blacklist_account_ids') or []))
    acc_id = str(acc.get('account_id') or '').strip()
    return bool(acc_id and acc_id in selected)

def _get_buyer_nick_from_event_message(event_msg) -> str:
    direct_attrs = ('author', 'author_name', 'sender_name', 'username', 'user_name', 'from_username', 'nickname', 'nick', 'login', 'buyer', 'buyer_username', 'buyer_name')
    for attr in direct_attrs:
        try:
            val = getattr(event_msg, attr, None)
            if isinstance(val, str) and val.strip():
                return val.strip()
        except Exception:
            pass
    nested_attrs = ('user', 'sender', 'from_user', 'author_obj', 'buyer_obj')
    nested_name_attrs = ('username', 'name', 'nickname', 'nick', 'login')
    for obj_attr in nested_attrs:
        try:
            obj = getattr(event_msg, obj_attr, None)
            if obj is None or isinstance(obj, str):
                continue
            for name_attr in nested_name_attrs:
                val = getattr(obj, name_attr, None)
                if isinstance(val, str) and val.strip():
                    return val.strip()
        except Exception:
            pass
    return ''

def _try_blacklist_reject(cardinal: 'Cardinal', owner_uid: str, acc: dict, buyer_id: str, buyer_nick: str, chat_id, cmd: str, cfg: dict) -> bool:
    if not _blacklist_applies_to_account(owner_uid, acc, cfg):
        return False
    matched_nick = _blacklist_match(cfg, buyer_nick)
    if not matched_nick:
        return False
    now = int(time.time())
    tpl = str(cfg.get('blacklist_text') or _default_cfg()['blacklist_text'])
    msg = _render_template(tpl, {'nick': buyer_nick, 'buyer_id': buyer_id, 'matched_nick': matched_nick, 'name': str(acc.get('name') or ''), 'command': cmd})
    cardinal.account.send_message(chat_id, msg)
    _push_log(owner_uid, {'ts': now, 'type': 'BLACKLIST', 'name': str(acc.get('name') or ''), 'cmd': cmd, 'buyer': buyer_id, 'nick': buyer_nick, 'msg': f'отклонён по чёрному списку: {matched_nick}'})
    return True

def _account_template_state(acc: dict) -> str:
    return 'свой' if str(acc.get('template') or '').strip() else 'общий'

def generate_steam_guard_code(shared_secret: str) -> Optional[str]:
    try:
        key = base64.b64decode(shared_secret)
        timestamp = int(time.time()) // 30
        msg = timestamp.to_bytes(8, byteorder='big')
        hmac_result = hmac.new(key, msg, digestmod='sha1').digest()
        offset = hmac_result[-1] & 15
        code_bytes = hmac_result[offset:offset + 4]
        full_code = int.from_bytes(code_bytes, byteorder='big') & 2147483647
        chars = '23456789BCDFGHJKMNPQRTVWXY'
        code = ''
        for _ in range(5):
            code += chars[full_code % len(chars)]
            full_code //= len(chars)
        return code
    except Exception as e:
        logger.error(f'{PREFIX} generate code error: {e}')
        return None

def _command_nick_slug(value: str) -> str:
    value = unicodedata.normalize('NFKC', str(value or '')).strip()
    if value.startswith('@'):
        value = value[1:].strip()
    value = value.casefold()
    while True:
        cleaned = re.sub('^[!/]?code(?:[_.\\-\\s]+|$)', '', value, count=1, flags=re.IGNORECASE)
        if cleaned == value:
            break
        value = cleaned.strip()
    result = []
    for ch in value:
        if ch.isalnum():
            result.append(ch)
        elif ch in {'_', '-', '.'} or ch.isspace():
            result.append('_')
    slug = re.sub('_+', '_', ''.join(result)).strip('_')
    return slug or 'account'

def _make_default_code_command(nick: str, accounts: List[dict]) -> str:
    base = f'!code_{_command_nick_slug(nick)}'
    used = {_normalize_cmd(str(acc.get('command') or '')) for acc in accounts if isinstance(acc, dict)}
    candidate = base
    number = 2
    while _normalize_cmd(candidate) in used:
        candidate = f'{base}_{number}'
        number += 1
    return _normalize_cmd(candidate)

def _extract_mafile_data(raw: bytes, filename: str) -> dict:
    if not isinstance(raw, (bytes, bytearray)) or not raw:
        raise ValueError('Файл пустой.')
    try:
        payload = json.loads(bytes(raw).decode('utf-8-sig'))
    except UnicodeDecodeError as e:
        raise ValueError('Не удалось прочитать кодировку файла.') from e
    except json.JSONDecodeError as e:
        raise ValueError('Внутри maFile некорректный JSON.') from e
    if not isinstance(payload, dict):
        raise ValueError('Некорректная структура maFile.')
    shared_secret = str(payload.get('shared_secret') or payload.get('sharedSecret') or '').strip()
    if not shared_secret:
        raise ValueError('В maFile не найден shared_secret.')
    if not generate_steam_guard_code(shared_secret):
        raise ValueError('В maFile найден невалидный shared_secret.')
    account_name = str(payload.get('account_name') or payload.get('accountName') or payload.get('login') or payload.get('username') or '').strip()
    if not account_name:
        account_name = os.path.splitext(os.path.basename(filename or 'account.maFile'))[0].strip()
    if not account_name:
        account_name = 'account'
    return {'shared_secret': shared_secret, 'account_name': account_name}

def _download_mafile(message: Message, bot) -> dict:
    document = getattr(message, 'document', None)
    if document is None:
        raise ValueError('Документ не найден.')
    filename = str(getattr(document, 'file_name', None) or 'account.maFile')
    if not filename.casefold().endswith('.mafile'):
        raise ValueError('Нужен файл с расширением .maFile.')
    file_size = int(getattr(document, 'file_size', 0) or 0)
    if file_size > 2 * 1024 * 1024:
        raise ValueError('maFile слишком большой. Максимальный размер — 2 МБ.')
    file_info = bot.get_file(document.file_id)
    raw = bot.download_file(file_info.file_path)
    return _extract_mafile_data(raw, filename)

def _mid(msg) -> int:
    return int(getattr(msg, 'message_id', None) or getattr(msg, 'id', 0) or 0)

def _strip_html_title(text: str) -> str:
    first = str(text or '').strip().splitlines()[0] if str(text or '').strip() else ''
    first = re.sub('<[^>]+>', '', first)
    return unescape(first).strip()[:180]

def _callback_action_label(data: str) -> str:
    raw = str(data or '')
    exact = {CB_WELCOME: 'открыто главное меню', CB_INFO: 'открыта информация о плагине', CB_SETTINGS: 'открыты настройки', CB_INSTRUCTION_ACK: 'подтверждено прочтение инструкции', CB_UPDATE_PLUGIN: 'открыто меню обновления', CB_UPDATE_PLUGIN_LOCAL: 'запущено локальное обновление', CB_UPDATE_PLUGIN_ONLINE: 'запущена онлайн-проверка обновления', CB_UPDATE_PLUGIN_YES: 'подтверждена установка обновления', CB_UPDATE_PLUGIN_NO: 'обновление отменено', CB_ADD: 'запущено добавление аккаунта', CB_LIST: 'открыт список аккаунтов', CB_DEL_MENU: 'открыто удаление аккаунтов', CB_TEMPLATE: 'открыто редактирование общего текста', CB_CONFIG_MENU: 'открыто меню конфигурации', CB_CONFIG_EXPORT: 'нажато скачивание конфигурации', CB_CONFIG_IMPORT: 'запущен импорт конфигурации', CB_BL: 'открыт чёрный список', CB_BL_NICKS: 'открыто управление никами ЧС', CB_BL_NICK_ADD: 'нажато добавление ника в ЧС', CB_BL_TEXT: 'открыто редактирование текста ЧС', CB_BL_ACCS: 'открыт выбор аккаунтов для ЧС', CB_PLUGIN_TOGGLE: 'переключено состояние плагина', CB_QUEUE_TOGGLE: 'переключена общая очередь', CB_CMD_NOTIFY_TOGGLE: 'переключены общие уведомления команд', CB_CANCEL: 'операция отменена', CB_DELETE_PLUGIN: 'открыто удаление плагина', CB_DELETE_PLUGIN_YES: 'подтверждено удаление плагина', CB_DELETE_PLUGIN_NO: 'удаление плагина отменено'}
    if raw in exact:
        return exact[raw]
    prefixes = [(CB_LOGS, 'открыта страница логов'), (CB_LIST_PAGE, 'переключена страница аккаунтов'), (CB_ACCOUNT_OPEN, 'открыта карточка аккаунта'), (CB_ACCOUNT_TOGGLE_ENABLED, 'переключена выдача кодов аккаунта'), (CB_ACCOUNT_TOGGLE_QUEUE, 'переключена очередь аккаунта'), (CB_ACCOUNT_TOGGLE_NOTIFY, 'переключены уведомления аккаунта'), (CB_ACCOUNT_EDIT_COMMAND, 'открыто изменение команды аккаунта'), (CB_ACCOUNT_TEXT_MENU, 'открыты настройки текста аккаунта'), (CB_ACCOUNT_TEXT_GLOBAL, 'выбран общий текст аккаунта'), (CB_ACCOUNT_TEXT_CUSTOM, 'открыто изменение личного текста аккаунта'), (CB_ACCOUNT_EDIT_SECRET, 'открыта замена secret/maFile'), (CB_ACCOUNT_EDIT_LIMIT, 'открыто изменение лимита аккаунта'), (CB_BL_NICK_PAGE, 'переключена страница ников ЧС'), (CB_BL_NICK_ADD, 'нажато добавление ника в ЧС'), (CB_BL_NICK_DEL, 'нажато удаление ника из ЧС'), (CB_BL_ACC_TOGGLE, 'переключён аккаунт для ЧС'), (CB_DEL_PICK, 'выбран аккаунт для удаления'), (CB_DEL_YES, 'подтверждено удаление аккаунта')]
    for prefix, label in prefixes:
        if raw.startswith(f'{prefix}:'):
            return label
    return f'нажата кнопка {raw[:120]}'

def _audit_callback(call):
    try:
        call_id = str(getattr(call, 'id', '') or '')
        now = time.time()
        with _ui_audit_lock:
            for old_id, ts in list(_recent_ui_callback_ids.items()):
                if now - ts > 180:
                    _recent_ui_callback_ids.pop(old_id, None)
            if call_id and call_id in _recent_ui_callback_ids:
                return
            if call_id:
                _recent_ui_callback_ids[call_id] = now
        message = getattr(call, 'message', None)
        chat = getattr(message, 'chat', None)
        chat_id = getattr(chat, 'id', None)
        if chat_id is None:
            return
        data = str(getattr(call, 'data', '') or '')
        current_screen = _strip_html_title(getattr(message, 'text', '') or '')
        _log_event(str(chat_id), 'UI_CLICK', _callback_action_label(data), callback=data[:220], screen=current_screen)
    except Exception:
        pass

def _safe_edit(bot, chat_id: int, msg_id: int, text: str, kb: Optional[InlineKeyboardMarkup]=None):
    try:
        bot.edit_message_text(text, chat_id, msg_id, parse_mode='HTML', reply_markup=kb, disable_web_page_preview=True)
        title = _strip_html_title(text)
        if title and 'Логи' not in title:
            _log_event(str(chat_id), 'SCREEN', f'Открыт экран: {title}', screen=title)
    except ApiTelegramException as e:
        if 'message is not modified' in str(e).lower():
            return
        _log_event(str(chat_id), 'ERROR', f'Не удалось открыть экран: {e}', where='_safe_edit')
        raise
    except Exception as e:
        _log_event(str(chat_id), 'ERROR', f'Ошибка интерфейса: {type(e).__name__}: {e}', where='_safe_edit')
        raise

def _try_delete(bot, chat_id: int, msg_id: int):
    try:
        bot.delete_message(chat_id, msg_id)
    except Exception:
        pass

def _answer_cbq(bot, call, text: Optional[str]=None, alert: bool=False):
    _audit_callback(call)
    try:
        if text is None:
            bot.answer_callback_query(call.id)
        else:
            bot.answer_callback_query(call.id, text, show_alert=alert)
    except Exception as e:
        try:
            chat_id = call.message.chat.id
            _log_event(str(chat_id), 'ERROR', f'Ошибка ответа на кнопку: {e}', where='_answer_cbq')
        except Exception:
            pass

def _cancel_kb(back_cb: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton('❌ Отменить', callback_data=CB_CANCEL), InlineKeyboardButton('◀️ Назад', callback_data=back_cb))
    return kb

def _add_command_choice_kb(suggested_command: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    shown = suggested_command
    if len(shown) > 42:
        shown = shown[:39] + '…'
    kb.row(InlineKeyboardButton(f'✅ Использовать {shown}', callback_data=CB_ADD_CMD_AUTO))
    kb.row(InlineKeyboardButton('✏️ Создать свою команду', callback_data=CB_ADD_CMD_CUSTOM))
    kb.row(InlineKeyboardButton('❌ Отменить', callback_data=CB_CANCEL), InlineKeyboardButton('◀️ Назад', callback_data=CB_SETTINGS))
    return kb

def _add_template_choice_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton('🌐 Общий текст', callback_data=CB_ADD_TEMPLATE_GLOBAL))
    kb.row(InlineKeyboardButton('✏️ Кастомный текст', callback_data=CB_ADD_TEMPLATE_CUSTOM))
    kb.row(InlineKeyboardButton('❌ Отменить', callback_data=CB_CANCEL), InlineKeyboardButton('◀️ Назад', callback_data=CB_SETTINGS))
    return kb

def _add_queue_choice_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton('✅ Добавить очередь', callback_data=CB_ADD_QUEUE_YES))
    kb.row(InlineKeyboardButton('🚫 Без очереди', callback_data=CB_ADD_QUEUE_NO))
    kb.row(InlineKeyboardButton('❌ Отменить', callback_data=CB_CANCEL), InlineKeyboardButton('◀️ Назад', callback_data=CB_SETTINGS))
    return kb

def _show_add_queue_choice(bot, chat_id: int, panel_msg_id: int, st: dict):
    st['step'] = 'queue_choice'
    _safe_edit(bot, chat_id, panel_msg_id, '⏳ <b>Очередь для аккаунта</b>\n\nДобавить функцию очереди для этого аккаунта?\n\n✅ <b>С очередью</b> — если код уже занят другим покупателем, следующий запрос будет поставлен в ожидание.\n🚫 <b>Без очереди</b> — покупателю предложат повторить запрос позже.', _add_queue_choice_kb())

def _welcome_text() -> str:
    return f'🧩 <b>Плагин:</b> <b>{NAME}</b>\n📦 <b>Версия:</b> {escape(VERSION)}\n👤 <b>Создатель:</b> <a href="{escape(CREATOR_URL)}">{escape(CREDITS)}</a>'

def _welcome_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton('⚙️ Настройки', callback_data=CB_SETTINGS), InlineKeyboardButton('ℹ️ Информация', callback_data=CB_INFO))
    kb.row(InlineKeyboardButton('⬆️ Обновить плагин', callback_data=CB_UPDATE_PLUGIN), InlineKeyboardButton('🗑 Удалить', callback_data=CB_DELETE_PLUGIN))
    kb.row(InlineKeyboardButton('🔙 К списку плагинов', callback_data=CBT_PLUGINS_LIST_OPEN))
    return kb

def _info_text() -> str:
    return ('ℹ️ <b>Информация</b>\n\nЗдесь находятся официальные ссылки Steam Guard (SDA).\n\n'
            '• <b>Чат</b> — помощь и общение.\n'
            '• <b>Канал</b> — новости и обновления.\n'
            '• <b>Инструкция</b> — настройка и использование плагина.\n'
            '• <b>Мой Telegram</b> — связь с автором.')

def _info_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton('💬 Чат', url=GROUP_URL), InlineKeyboardButton('📢 Канал', url=CHANNEL_URL))
    kb.row(InlineKeyboardButton('📖 Инструкция', url=INSTRUCTION_URL))
    kb.row(InlineKeyboardButton('👤 Мой Telegram', url=CREATOR_URL))
    kb.row(InlineKeyboardButton('◀️ Назад', callback_data=CB_WELCOME))
    return kb

def open_information(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    _safe_edit(bot, call.message.chat.id, _mid(call.message), _info_text(), _info_kb())

def open_welcome(cardinal: 'Cardinal', call_or_msg):
    bot = cardinal.telegram.bot
    text = _welcome_text()
    kb = _welcome_kb()
    if hasattr(call_or_msg, 'message'):
        _answer_cbq(bot, call_or_msg)
        chat_id = call_or_msg.message.chat.id
        msg_id = _mid(call_or_msg.message)
        _safe_edit(bot, chat_id, msg_id, text, kb)
    else:
        chat_id = call_or_msg.chat.id
        _log_event(str(chat_id), 'ACTION', 'Главное меню открыто командой /sda_menu')
        bot.send_message(chat_id, text, parse_mode='HTML', reply_markup=kb, disable_web_page_preview=True)

def _settings_text(chat_id: int) -> str:
    data = load_data()
    cfg = _get_cfg(data)
    accounts = _get_accounts_for(chat_id, data)
    save_data(data)
    tpl = (cfg.get('template') or '').strip()
    tpl_short = tpl[:120] + '…' if len(tpl) > 120 else tpl or '—'
    plugin_state = 'ВКЛ' if bool(cfg.get('plugin_enabled', True)) else 'ВЫКЛ'
    queue_state = 'ВКЛ' if bool(cfg.get('queue_enabled', True)) else 'ВЫКЛ'
    cmd_notify_state = 'ВКЛ' if bool(cfg.get('command_notifications_enabled', True)) else 'ВЫКЛ'
    bl_state = 'ВКЛ' if bool(cfg.get('blacklist_enabled', False)) else 'ВЫКЛ'
    bl_nicks_count = len(cfg.get('blacklist_nicks') or [])
    bl_scope = _blacklist_scope_label(str(cfg.get('blacklist_scope') or 'all'))
    return f'⚙️ <b>Настройки</b>\n\nПлагин: <b>{plugin_state}</b>\nАккаунтов: <b>{len(accounts)}</b>\nОчередь: <b>{queue_state}</b>\nУведомления команд: <b>{cmd_notify_state}</b>\nЧёрный список: <b>{bl_state}</b> | ников: <b>{bl_nicks_count}</b> | режим: <b>{escape(bl_scope)}</b>\nОбщий текст ответа:\n<code>{escape(tpl_short)}</code>\n\nВыбери действие:'

def _settings_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    plugin_state = 'ВКЛ' if _plugin_enabled() else 'ВЫКЛ'
    kb.row(InlineKeyboardButton(f'🔌 Плагин: {plugin_state}', callback_data=CB_PLUGIN_TOGGLE))
    kb.row(InlineKeyboardButton('➕ Добавить аккаунт', callback_data=CB_ADD), InlineKeyboardButton('📜 Список аккаунтов', callback_data=CB_LIST))
    kb.row(InlineKeyboardButton('🗑 Удалить аккаунт', callback_data=CB_DEL_MENU), InlineKeyboardButton('🧾 Логи', callback_data=f'{CB_LOGS}:0'))
    queue_state = 'ВКЛ' if _queue_enabled() else 'ВЫКЛ'
    kb.row(InlineKeyboardButton(f'⏳ Очередь: {queue_state}', callback_data=CB_QUEUE_TOGGLE))
    cmd_notify_state = 'ВКЛ' if _command_notifications_enabled() else 'ВЫКЛ'
    kb.row(InlineKeyboardButton(f'🔔 Уведомления команд: {cmd_notify_state}', callback_data=CB_CMD_NOTIFY_TOGGLE))
    kb.row(InlineKeyboardButton('✏️ Общий текст', callback_data=CB_TEMPLATE))
    kb.row(InlineKeyboardButton('📦 Конфиг', callback_data=CB_CONFIG_MENU))
    kb.row(InlineKeyboardButton('🚫 Чёрный список', callback_data=CB_BL))
    kb.row(InlineKeyboardButton('◀️ Назад', callback_data=CB_WELCOME))
    return kb

def _instruction_acknowledged(chat_id: int) -> bool:
    data = load_data()
    cfg = _get_cfg(data)
    save_data(data)
    return str(chat_id) in set(cfg.get('instruction_acknowledged_chat_ids') or [])

def _set_instruction_acknowledged(chat_id: int):
    data = load_data()
    cfg = _get_cfg(data)
    ids = list(cfg.get('instruction_acknowledged_chat_ids') or [])
    uid = str(chat_id)
    if uid not in ids:
        ids.append(uid)
    cfg['instruction_acknowledged_chat_ids'] = ids
    data['global'] = cfg
    save_data(data)

def _first_settings_notice_text() -> str:
    return ('📖 <b>Перед началом работы</b>\n\n'
            'Перед первым входом в настройки необходимо ознакомиться с инструкцией по установке и использованию Steam Guard (SDA).\n\n'
            '1. Нажмите <b>«Открыть инструкцию»</b>.\n'
            '2. Прочитайте её полностью.\n'
            '3. Вернитесь сюда и нажмите <b>«Я прочитал инструкцию»</b>.\n\n'
            'После подтверждения этот экран больше показываться не будет.')

def _first_settings_notice_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton('📖 Открыть инструкцию', url=INSTRUCTION_URL))
    kb.row(InlineKeyboardButton('✅ Я прочитал инструкцию', callback_data=CB_INSTRUCTION_ACK))
    kb.row(InlineKeyboardButton('◀️ Назад', callback_data=CB_WELCOME))
    return kb

def open_settings(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    if not _instruction_acknowledged(chat_id):
        _safe_edit(bot, chat_id, msg_id, _first_settings_notice_text(), _first_settings_notice_kb())
        return
    _safe_edit(bot, chat_id, msg_id, _settings_text(chat_id), _settings_kb())

def acknowledge_instruction(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call, 'Подтверждение сохранено.')
    chat_id = call.message.chat.id
    _set_instruction_acknowledged(chat_id)
    _log_event(str(chat_id), 'SETTINGS', 'Пользователь подтвердил прочтение инструкции')
    _safe_edit(bot, chat_id, _mid(call.message), _settings_text(chat_id), _settings_kb())

def _update_menu_text() -> str:
    return (f'⬆️ <b>Обновление {escape(NAME)}</b>\n\n'
            f'Текущая версия: <b>{escape(VERSION)}</b>\n\n'
            '• <b>Обновить локально</b> — отправить новый файл плагина <code>.py</code>.\n'
            '• <b>Обновить онлайн</b> — скачать и проверить файл из GitHub.\n\n'
            'Перед заменой создаётся резервная копия текущего файла. Аккаунты, конфиг, логи и очередь не удаляются.')

def _update_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton('📥 Обновить локально', callback_data=CB_UPDATE_PLUGIN_LOCAL))
    kb.row(InlineKeyboardButton('🌐 Обновить онлайн', callback_data=CB_UPDATE_PLUGIN_ONLINE))
    kb.row(InlineKeyboardButton('◀️ Назад', callback_data=CB_WELCOME))
    return kb

def open_update_menu(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    _safe_edit(bot, call.message.chat.id, _mid(call.message), _update_menu_text(), _update_menu_kb())

def start_local_plugin_update(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    chat_id = call.message.chat.id
    _answer_cbq(bot, call, 'Пришлите файл плагина .py')
    _fsm[chat_id] = {'mode': 'plugin_update_local', 'step': 'document', 'panel_chat_id': chat_id, 'panel_msg_id': _mid(call.message), 'return': CB_UPDATE_PLUGIN}
    _safe_edit(bot, chat_id, _mid(call.message), '📥 <b>Локальное обновление</b>\n\nОтправьте новый файл Steam Guard (SDA) с расширением <code>.py</code>.\n\nФайл будет проверен перед установкой. Текущий плагин сохранится в резервной копии, а данные останутся на месте.', _cancel_kb(CB_UPDATE_PLUGIN))

def _plugin_version_from_source(source: str) -> Optional[str]:
    match = re.search(r'(?m)^\s*VERSION\s*=\s*["\']([^"\']+)["\']', source or '')
    return match.group(1).strip() if match else None

def _cleanup_plugin_bytecode(plugin_file: str):
    try:
        cache = os.path.join(os.path.dirname(plugin_file), '__pycache__')
        if not os.path.isdir(cache):
            return
        base = os.path.splitext(os.path.basename(plugin_file))[0]
        for filename in os.listdir(cache):
            if filename.startswith(base + '.') and filename.endswith('.pyc'):
                try:
                    os.remove(os.path.join(cache, filename))
                except Exception:
                    pass
    except Exception:
        pass

def _validate_plugin_update_payload(payload, plugin_file: Optional[str] = None):
    plugin_file = os.path.abspath(plugin_file or __file__)
    if not isinstance(payload, (bytes, bytearray)):
        raise RuntimeError('файл обновления не прочитан')
    payload = bytes(payload)
    if len(payload) < 10000:
        raise RuntimeError(f'файл обновления слишком маленький ({len(payload)} байт)')
    if len(payload) > 5 * 1024 * 1024:
        raise RuntimeError('файл обновления слишком большой (>5 МБ)')
    try:
        source = payload.decode('utf-8-sig')
    except UnicodeDecodeError as error:
        raise RuntimeError(f'файл обновления не UTF-8: {error}') from error
    if '<html' in source[:700].lower() or '<!doctype' in source[:700].lower():
        raise RuntimeError('вместо Python-файла получена HTML-страница')
    missing = [value for value in (NAME, 'def init_cardinal', 'BIND_TO_PRE_INIT', 'BIND_TO_NEW_MESSAGE') if value not in source]
    if missing:
        raise RuntimeError('это не файл Steam Guard (SDA): нет ' + ', '.join(missing))
    if UUID not in source:
        raise RuntimeError('UUID загруженного плагина не совпадает')
    remote_version = _plugin_version_from_source(source)
    if not remote_version:
        raise RuntimeError('в файле обновления не найдена VERSION')
    compile(source, plugin_file, 'exec')
    return source, remote_version, hashlib.sha256(payload).hexdigest()

def _install_plugin_payload(payload, source_name: str = 'update') -> dict:
    plugin_file = os.path.abspath(__file__)
    stamp = time.strftime('%Y%m%d-%H%M%S')
    backup_file = plugin_file + f'.pre-update.{stamp}.bak'
    tmp_file = plugin_file + '.update.tmp'
    result = {'ok': False, 'changed': False, 'current_version': VERSION, 'remote_version': None, 'backup_file': backup_file, 'error': None}
    try:
        _, remote_version, remote_hash = _validate_plugin_update_payload(payload, plugin_file)
        result['remote_version'] = remote_version
        with open(plugin_file, 'rb') as file:
            current_payload = file.read()
        if hashlib.sha256(current_payload).hexdigest() == remote_hash:
            result.update(ok=True, changed=False)
            return result
        with open(tmp_file, 'wb') as file:
            file.write(bytes(payload))
            file.flush()
            os.fsync(file.fileno())
        try:
            os.chmod(tmp_file, os.stat(plugin_file).st_mode)
        except Exception:
            pass
        shutil.copy2(plugin_file, backup_file)
        os.replace(tmp_file, plugin_file)
        _cleanup_plugin_bytecode(plugin_file)
        result.update(ok=True, changed=True)
        logger.warning(f'{PREFIX} plugin updated from {source_name}: {VERSION} -> {remote_version}; backup={backup_file}')
    except Exception as error:
        result['error'] = str(error)
        logger.exception(f'{PREFIX} plugin update failed: {error}')
        try:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)
        except Exception:
            pass
    return result

def _download_local_update_document(message: Message, bot):
    document = getattr(message, 'document', None)
    if document is None:
        raise RuntimeError('документ не найден')
    filename = str(getattr(document, 'file_name', None) or 'SteamGuardSDA.py')
    if not filename.casefold().endswith('.py'):
        raise RuntimeError('нужен файл с расширением .py')
    size = int(getattr(document, 'file_size', 0) or 0)
    if size > 5 * 1024 * 1024:
        raise RuntimeError('файл обновления слишком большой (>5 МБ)')
    info = bot.get_file(document.file_id)
    payload = bot.download_file(info.file_path)
    return filename, payload

def _handle_local_plugin_update_document(message: Message, cardinal: 'Cardinal', state: dict):
    bot = cardinal.telegram.bot
    chat_id = message.chat.id
    panel_msg_id = int(state.get('panel_msg_id') or 0)
    try:
        filename, payload = _download_local_update_document(message, bot)
        result = _install_plugin_payload(payload, f'локального файла {filename}')
        _fsm.pop(chat_id, None)
        if result.get('ok') and result.get('changed'):
            text = (f'✅ <b>Локальное обновление установлено.</b>\n\nФайл: <code>{escape(filename)}</code>\n'
                    f'Версия: <b>{escape(str(result.get("current_version")))}</b> → <b>{escape(str(result.get("remote_version")))}</b>\n'
                    f'Резервная копия: <code>{escape(os.path.basename(str(result.get("backup_file") or "")))}</code>\n'
                    'Аккаунты, конфиг, логи и очередь сохранены.\n\n🔁 Выполните <code>/restart</code>.')
        elif result.get('ok'):
            text = '✅ <b>Этот файл уже установлен.</b>\n\nОсновной файл и данные не изменены.'
        else:
            text = f'❌ <b>Локальное обновление не установлено.</b>\n\nОшибка: <code>{escape(str(result.get("error") or "неизвестная ошибка"))}</code>\n\nТекущий файл и данные не изменены.'
        if panel_msg_id:
            _safe_edit(bot, chat_id, panel_msg_id, text, _update_menu_kb())
    except Exception as error:
        if panel_msg_id:
            _safe_edit(bot, chat_id, panel_msg_id, f'❌ <b>Не удалось обработать обновление.</b>\n\nОшибка: <code>{escape(str(error))}</code>\n\nОтправьте корректный файл <code>.py</code>.', _cancel_kb(CB_UPDATE_PLUGIN))

def _pending_update_file() -> str:
    return os.path.abspath(__file__) + '.update.pending'

def _download_online_plugin_update() -> dict:
    from urllib.request import Request, urlopen
    pending_file = _pending_update_file()
    result = {'ok': False, 'changed': False, 'current_version': VERSION, 'remote_version': None, 'pending_file': pending_file, 'error': None}
    try:
        if not SDA_UPDATE_URL.lower().startswith('https://'):
            raise RuntimeError('SDA_PLUGIN_UPDATE_URL должен использовать HTTPS')
        request = Request(SDA_UPDATE_URL, headers={'Accept': 'text/plain, application/octet-stream;q=0.9, */*;q=0.1', 'User-Agent': f'{NAME}/{VERSION} self-updater', 'Cache-Control': 'no-cache'})
        with urlopen(request, timeout=45) as response:
            payload = response.read(5 * 1024 * 1024 + 1)
        _, remote_version, remote_hash = _validate_plugin_update_payload(payload)
        result['remote_version'] = remote_version
        with open(os.path.abspath(__file__), 'rb') as file:
            current_hash = hashlib.sha256(file.read()).hexdigest()
        if current_hash == remote_hash:
            try:
                if os.path.exists(pending_file):
                    os.remove(pending_file)
            except Exception:
                pass
            result.update(ok=True, changed=False)
            return result
        with open(pending_file, 'wb') as file:
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
        result.update(ok=True, changed=True)
    except Exception as error:
        result['error'] = str(error)
        logger.exception(f'{PREFIX} online update check failed: {error}')
        try:
            if os.path.exists(pending_file):
                os.remove(pending_file)
        except Exception:
            pass
    return result

def check_online_plugin_update(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    chat_id = call.message.chat.id
    _answer_cbq(bot, call, 'Проверяю обновление онлайн…')
    _safe_edit(bot, chat_id, _mid(call.message), '⏬ <b>Проверяю обновление…</b>\n\nСкачиваю файл и проверяю UUID, синтаксис и целостность.', None)
    result = _download_online_plugin_update()
    kb = InlineKeyboardMarkup()
    if result.get('ok') and result.get('changed'):
        kb.row(InlineKeyboardButton('✅ Установить', callback_data=CB_UPDATE_PLUGIN_YES), InlineKeyboardButton('❌ Отмена', callback_data=CB_UPDATE_PLUGIN_NO))
        if SDA_GITHUB_URL:
            kb.row(InlineKeyboardButton('🌐 GitHub', url=SDA_GITHUB_URL), InlineKeyboardButton('◀️ Назад', callback_data=CB_UPDATE_PLUGIN))
        text = (f'🆕 <b>Найден другой файл плагина.</b>\n\nТекущая версия: <b>{escape(VERSION)}</b>\n'
                f'Версия файла: <b>{escape(str(result.get("remote_version") or "не определена"))}</b>\n\n'
                'Проверка пройдена. Даже если номер версии совпадает, обновление доступно, потому что содержимое файла отличается.')
    elif result.get('ok'):
        if SDA_GITHUB_URL:
            kb.row(InlineKeyboardButton('🌐 GitHub', url=SDA_GITHUB_URL), InlineKeyboardButton('◀️ Назад', callback_data=CB_UPDATE_PLUGIN))
        else:
            kb.row(InlineKeyboardButton('◀️ Назад', callback_data=CB_UPDATE_PLUGIN))
        text = f'✅ <b>Обновление не требуется.</b>\n\nУстановлена версия: <b>{escape(VERSION)}</b>\nОнлайн-версия: <b>{escape(str(result.get("remote_version") or "не определена"))}</b>\n\nСодержимое файлов совпадает.'
    else:
        if SDA_GITHUB_URL:
            kb.row(InlineKeyboardButton('🌐 GitHub', url=SDA_GITHUB_URL), InlineKeyboardButton('◀️ Назад', callback_data=CB_UPDATE_PLUGIN))
        else:
            kb.row(InlineKeyboardButton('◀️ Назад', callback_data=CB_UPDATE_PLUGIN))
        text = f'❌ <b>Не удалось проверить обновление.</b>\n\nОшибка: <code>{escape(str(result.get("error") or "неизвестная ошибка"))}</code>\n\nТекущий файл и данные не изменены.'
    _safe_edit(bot, chat_id, _mid(call.message), text, kb)

def install_online_plugin_update(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    chat_id = call.message.chat.id
    _answer_cbq(bot, call, 'Устанавливаю обновление…')
    pending_file = _pending_update_file()
    try:
        if not os.path.isfile(pending_file):
            raise RuntimeError('файл обновления не найден; сначала выполните онлайн-проверку')
        with open(pending_file, 'rb') as file:
            payload = file.read()
        result = _install_plugin_payload(payload, 'онлайн-источника')
        try:
            os.remove(pending_file)
        except Exception:
            pass
        if result.get('ok') and result.get('changed'):
            text = (f'✅ <b>Плагин обновлён.</b>\n\nВерсия: <b>{escape(str(result.get("current_version")))}</b> → <b>{escape(str(result.get("remote_version")))}</b>\n'
                    f'Резервная копия: <code>{escape(os.path.basename(str(result.get("backup_file") or "")))}</code>\n'
                    'Аккаунты, конфиг, логи и очередь сохранены.\n\n🔁 Выполните <code>/restart</code>.')
        elif result.get('ok'):
            text = '✅ <b>Этот файл уже установлен.</b>\n\nОсновной файл и данные не изменены.'
        else:
            text = f'❌ <b>Не удалось установить обновление.</b>\n\nОшибка: <code>{escape(str(result.get("error") or "неизвестная ошибка"))}</code>'
    except Exception as error:
        text = f'❌ <b>Не удалось установить обновление.</b>\n\nОшибка: <code>{escape(str(error))}</code>'
    _safe_edit(bot, chat_id, _mid(call.message), text, _update_menu_kb())

def cancel_online_plugin_update(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    try:
        pending_file = _pending_update_file()
        if os.path.exists(pending_file):
            os.remove(pending_file)
    except Exception:
        pass
    _answer_cbq(bot, call, 'Обновление отменено.')
    _safe_edit(bot, call.message.chat.id, _mid(call.message), '❌ <b>Обновление отменено.</b>\n\nФайл плагина и данные не изменены.', _update_menu_kb())

def _config_menu_text(chat_id: int) -> str:
    data = load_data()
    accounts = _get_accounts_for(chat_id, data)
    return f'📦 <b>Конфигурация плагина</b>\n\nАккаунтов в текущей конфигурации: <b>{len(accounts)}</b>.\n\n• <b>Скачать конфиг</b> — получить JSON-файл с общими настройками и аккаунтами.\n• <b>Импортировать</b> — заменить текущие настройки данными из JSON-файла.\n\n⚠️ Файл содержит <code>shared_secret</code>. Не передавайте его посторонним.'

def _config_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton('📤 Скачать конфиг', callback_data=CB_CONFIG_EXPORT))
    kb.row(InlineKeyboardButton('📥 Импортировать конфиг', callback_data=CB_CONFIG_IMPORT))
    kb.row(InlineKeyboardButton('◀️ Назад в настройки', callback_data=CB_SETTINGS))
    return kb

def open_config_menu(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    chat_id = call.message.chat.id
    _safe_edit(bot, chat_id, _mid(call.message), _config_menu_text(chat_id), _config_menu_kb())
CONFIG_FORMAT = 'steam_guard_sda_config'
CONFIG_SCHEMA_VERSION = 1
CONFIG_MAX_FILE_SIZE = 5 * 1024 * 1024
CONFIG_MAX_ACCOUNTS = 500

def _build_config_payload(chat_id: int) -> dict:
    data = load_data()
    cfg = _get_cfg(data)
    accounts = _get_accounts_for(chat_id, data)
    save_data(data)
    return {'format': CONFIG_FORMAT, 'schema_version': CONFIG_SCHEMA_VERSION, 'plugin_version': VERSION, 'exported_at': int(time.time()), 'global': cfg, 'accounts': accounts}

def export_config(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    chat_id = call.message.chat.id
    _answer_cbq(bot, call, 'Формирую конфиг…')
    try:
        payload = _build_config_payload(chat_id)
        raw = json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8')
        document = io.BytesIO(raw)
        document.name = f"steam_guard_sda_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        document.seek(0)
        _log_event(str(chat_id), 'CONFIG', 'Конфигурация экспортирована', accounts=len(payload.get('accounts') or []))
        bot.send_document(chat_id, document, caption='📤 <b>Конфиг Steam Guard SDA</b>\n\n⚠️ В файле находятся <code>shared_secret</code> аккаунтов. Не передавайте его посторонним.', parse_mode='HTML')
    except Exception as e:
        logger.exception(f'{PREFIX} config export error: {e}')
        _log_event(str(chat_id), 'ERROR', f'Ошибка экспорта конфига: {type(e).__name__}: {e}', where='export_config')
        try:
            bot.send_message(chat_id, '❌ Не удалось сформировать файл конфигурации.')
        except Exception:
            pass

def start_config_import(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    _answer_cbq(bot, call)
    _fsm[chat_id] = {'mode': 'config_import', 'step': 'document', 'panel_chat_id': chat_id, 'panel_msg_id': msg_id, 'return': CB_CONFIG_MENU}
    _safe_edit(bot, chat_id, msg_id, '📥 <b>Импорт конфигурации</b>\n\nОтправьте JSON-файл, ранее скачанный через кнопку <b>«Скачать конфиг»</b>.\n\nИмпорт заменит общие настройки и список аккаунтов этого плагина. Логи и статистика использования не импортируются.\n\n⚠️ Файл после обработки будет удалён из чата.', _cancel_kb(CB_CONFIG_MENU))

def _download_json_document(message: Message, bot) -> dict:
    document = getattr(message, 'document', None)
    if document is None:
        raise ValueError('Документ не найден.')
    filename = str(getattr(document, 'file_name', None) or 'config.json')
    if not filename.casefold().endswith('.json'):
        raise ValueError('Нужен файл с расширением .json.')
    file_size = int(getattr(document, 'file_size', 0) or 0)
    if file_size > CONFIG_MAX_FILE_SIZE:
        raise ValueError('Файл слишком большой. Максимальный размер — 5 МБ.')
    file_info = bot.get_file(document.file_id)
    raw = bot.download_file(file_info.file_path)
    if len(raw) > CONFIG_MAX_FILE_SIZE:
        raise ValueError('Файл слишком большой. Максимальный размер — 5 МБ.')
    try:
        payload = json.loads(bytes(raw).decode('utf-8-sig'))
    except UnicodeDecodeError as e:
        raise ValueError('Не удалось прочитать кодировку JSON-файла.') from e
    except json.JSONDecodeError as e:
        raise ValueError('В файле находится некорректный JSON.') from e
    if not isinstance(payload, dict):
        raise ValueError('Корень конфигурации должен быть JSON-объектом.')
    return payload

def _parse_import_positive_int(value, field_name: str, allow_none: bool=True):
    if value is None and allow_none:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as e:
        raise ValueError(f'Поле {field_name} должно быть положительным числом или null.') from e
    if parsed <= 0:
        raise ValueError(f'Поле {field_name} должно быть больше нуля.')
    return parsed

def _validate_imported_config(payload: dict) -> tuple[dict, List[dict]]:
    if str(payload.get('format') or '') != CONFIG_FORMAT:
        raise ValueError('Это не конфиг Steam Guard SDA или у него неподдерживаемый формат.')
    try:
        schema_version = int(payload.get('schema_version') or 0)
    except (TypeError, ValueError):
        schema_version = 0
    if schema_version != CONFIG_SCHEMA_VERSION:
        raise ValueError(f'Неподдерживаемая версия конфига: {schema_version}.')
    raw_cfg = payload.get('global')
    raw_accounts = payload.get('accounts')
    if not isinstance(raw_cfg, dict):
        raise ValueError('В конфиге отсутствует объект global.')
    if not isinstance(raw_accounts, list):
        raise ValueError('В конфиге отсутствует список accounts.')
    if len(raw_accounts) > CONFIG_MAX_ACCOUNTS:
        raise ValueError(f'Слишком много аккаунтов. Максимум: {CONFIG_MAX_ACCOUNTS}.')
    cfg_box = {'global': dict(raw_cfg)}
    cfg = dict(_get_cfg(cfg_box))
    cfg['template_mode'] = 'global'
    accounts: List[dict] = []
    used_commands = set()
    used_ids = set()
    for pos, raw_acc in enumerate(raw_accounts, start=1):
        if not isinstance(raw_acc, dict):
            raise ValueError(f'Аккаунт №{pos} имеет некорректную структуру.')
        name = str(raw_acc.get('name') or f'Аккаунт {pos}').strip()
        command = _normalize_cmd(str(raw_acc.get('command') or ''))
        shared_secret = str(raw_acc.get('shared_secret') or '').strip()
        if not command:
            raise ValueError(f'У аккаунта №{pos} отсутствует команда.')
        if command in {'sda_menu', '/sda_menu'} or command.lstrip('/') == 'sda_menu':
            raise ValueError(f'У аккаунта №{pos} используется зарезервированная команда.')
        if command in used_commands:
            raise ValueError(f'Команда {command} встречается в конфиге несколько раз.')
        if not generate_steam_guard_code(shared_secret):
            raise ValueError(f'У аккаунта №{pos} невалидный shared_secret.')
        limit = _parse_import_positive_int(raw_acc.get('limit'), f'limit аккаунта №{pos}')
        if limit is None:
            period_hours = None
        else:
            period_hours = _parse_import_positive_int(raw_acc.get('period_hours'), f'period_hours аккаунта №{pos}')
        acc = {'name': name or f'Аккаунт {pos}', 'command': command, 'shared_secret': shared_secret, 'limit': limit, 'period_hours': period_hours, 'template': str(raw_acc.get('template') or '').strip(), 'enabled': bool(raw_acc.get('enabled', True)), 'queue_enabled': bool(raw_acc.get('queue_enabled', True)), 'command_notifications_enabled': bool(raw_acc.get('command_notifications_enabled', True))}
        account_id = str(raw_acc.get('account_id') or '').strip()
        if re.fullmatch('[a-f0-9]{10}', account_id) and account_id not in used_ids:
            acc['account_id'] = account_id
            used_ids.add(account_id)
        used_commands.add(command)
        accounts.append(acc)
    _ensure_account_ids('import', accounts)
    valid_ids = {str(acc.get('account_id') or '') for acc in accounts}
    cfg['blacklist_account_ids'] = [str(account_id) for account_id in cfg.get('blacklist_account_ids') or [] if str(account_id) in valid_ids]
    return (cfg, accounts)

def _clear_owner_runtime_queue(owner_uid: str):
    prefix = f'{owner_uid}::'
    with _queue_lock:
        queue_data = load_queue()
        keys = [key for key in queue_data if str(key).startswith(prefix)]
        for key in keys:
            queue_data.pop(key, None)
            _cancel_timer(key)
        save_queue(queue_data)

def _handle_config_import_document(message: Message, cardinal: 'Cardinal', st: dict):
    bot = cardinal.telegram.bot
    chat_id = message.chat.id
    panel_msg_id = int(st.get('panel_msg_id') or 0)
    try:
        payload = _download_json_document(message, bot)
        cfg, accounts = _validate_imported_config(payload)
        data = load_data()
        data['global'] = cfg
        _set_accounts_for(chat_id, data, accounts)
        save_data(data)
        _clear_owner_runtime_queue(str(chat_id))
        _cancel_all_queue_timers()
        _reschedule_available_queues(cardinal)
        _log_event(str(chat_id), 'CONFIG', 'Конфигурация импортирована', accounts=len(accounts))
        _fsm.pop(chat_id, None)
        if panel_msg_id:
            _safe_edit(bot, chat_id, panel_msg_id, f'✅ <b>Конфигурация импортирована</b>\n\nАккаунтов загружено: <b>{len(accounts)}</b>.\nОбщие настройки и настройки аккаунтов заменены.', _config_menu_kb())
    except ValueError as e:
        _log_event(str(chat_id), 'ERROR', f'Конфиг отклонён: {e}', where='config_import_validation')
        if panel_msg_id:
            _safe_edit(bot, chat_id, panel_msg_id, f'❌ <b>Не удалось импортировать конфиг</b>\n\n{escape(str(e))}\n\nОтправьте исправленный JSON-файл.', _cancel_kb(CB_CONFIG_MENU))
    except Exception as e:
        logger.exception(f'{PREFIX} config import error: {e}')
        _log_event(str(chat_id), 'ERROR', f'Ошибка импорта конфига: {type(e).__name__}: {e}', where='config_import')
        if panel_msg_id:
            _safe_edit(bot, chat_id, panel_msg_id, '❌ Произошла ошибка при импорте конфигурации.', _cancel_kb(CB_CONFIG_MENU))

def _blacklist_panel_text(chat_id: int) -> str:
    data = load_data()
    cfg = _get_cfg(data)
    accounts = _get_accounts_for(chat_id, data)
    save_data(data)
    enabled = bool(cfg.get('blacklist_enabled', False))
    state = 'ВКЛ' if enabled else 'ВЫКЛ'
    nicks = cfg.get('blacklist_nicks') or []
    nicks_preview = ', '.join((str(x) for x in nicks[:25]))
    if len(nicks) > 25:
        nicks_preview += f' … +{len(nicks) - 25}'
    if not nicks_preview:
        nicks_preview = '—'
    selected_ids = set((str(x) for x in cfg.get('blacklist_account_ids') or []))
    selected_count = 0
    for acc in accounts:
        if str(acc.get('account_id') or '') in selected_ids:
            selected_count += 1
    scope = str(cfg.get('blacklist_scope') or 'all')
    scope_label = _blacklist_scope_label(scope)
    tpl = str(cfg.get('blacklist_text') or _default_cfg()['blacklist_text'])
    tpl_short = tpl[:160] + '…' if len(tpl) > 160 else tpl
    return f'🚫 <b>Чёрный список</b>\n\nСостояние: <b>{state}</b>\nПрименение: <b>{escape(scope_label)}</b>\nНиков в списке: <b>{len(nicks)}</b>\nВыбранных аккаунтов: <b>{selected_count}</b>\n\n💬 <b>Текст ответа:</b>\n<code>{escape(tpl_short)}</code>\n\n'

def _blacklist_kb() -> InlineKeyboardMarkup:
    data = load_data()
    cfg = _get_cfg(data)
    kb = InlineKeyboardMarkup()
    state = 'ВКЛ' if bool(cfg.get('blacklist_enabled', False)) else 'ВЫКЛ'
    scope_label = _blacklist_scope_label(str(cfg.get('blacklist_scope') or 'all'))
    kb.row(InlineKeyboardButton(f'🚫 ЧС: {state}', callback_data=CB_BL_TOGGLE))
    kb.row(InlineKeyboardButton(f'🎯 Применение: {scope_label}', callback_data=CB_BL_SCOPE))
    kb.row(InlineKeyboardButton('👤 Ники', callback_data=CB_BL_NICKS), InlineKeyboardButton('💬 Текст ответа', callback_data=CB_BL_TEXT))
    kb.row(InlineKeyboardButton('✅ Выбрать аккаунты', callback_data=CB_BL_ACCS))
    kb.row(InlineKeyboardButton('◀️ Назад', callback_data=CB_SETTINGS))
    return kb

def open_blacklist(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    _safe_edit(bot, chat_id, msg_id, _blacklist_panel_text(chat_id), _blacklist_kb())

def toggle_blacklist(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    data = load_data()
    cfg = _get_cfg(data)
    cfg['blacklist_enabled'] = not bool(cfg.get('blacklist_enabled', False))
    data['global'] = cfg
    save_data(data)
    _answer_cbq(bot, call, f"Чёрный список {('включён' if cfg['blacklist_enabled'] else 'выключен')}.")
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    _safe_edit(bot, chat_id, msg_id, _blacklist_panel_text(chat_id), _blacklist_kb())

def toggle_blacklist_scope(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    data = load_data()
    cfg = _get_cfg(data)
    current = str(cfg.get('blacklist_scope') or 'all')
    cfg['blacklist_scope'] = 'selected' if current == 'all' else 'all'
    data['global'] = cfg
    save_data(data)
    _answer_cbq(bot, call, f"Режим: {_blacklist_scope_label(cfg['blacklist_scope'])}.")
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    _safe_edit(bot, chat_id, msg_id, _blacklist_panel_text(chat_id), _blacklist_kb())
BLACKLIST_NICKS_PAGE_SIZE = 5

def _clamp_blacklist_nick_page(total: int, page: int) -> tuple[int, int]:
    total_pages = max(1, (max(0, int(total)) + BLACKLIST_NICKS_PAGE_SIZE - 1) // BLACKLIST_NICKS_PAGE_SIZE)
    return (max(0, min(int(page), total_pages - 1)), total_pages)

def _blacklist_nicks_text(chat_id: int, page: int=0, notice: str='') -> str:
    data = load_data()
    cfg = _get_cfg(data)
    nicks = list(cfg.get('blacklist_nicks') or [])
    page, total_pages = _clamp_blacklist_nick_page(len(nicks), page)
    prefix = f'{notice}\n\n' if notice else ''
    return prefix + '👤 <b>Ники чёрного списка</b>\n\n' + 'Добавляйте ники по одному. Чтобы удалить ник, нажмите кнопку с ним ниже.\n\n' + f'Ников: <b>{len(nicks)}</b>\n' + f'Страница: <b>{page + 1}/{total_pages}</b>'

def _blacklist_nicks_kb(chat_id: int, page: int=0) -> InlineKeyboardMarkup:
    data = load_data()
    cfg = _get_cfg(data)
    nicks = list(cfg.get('blacklist_nicks') or [])
    page, total_pages = _clamp_blacklist_nick_page(len(nicks), page)
    start = page * BLACKLIST_NICKS_PAGE_SIZE
    chunk = nicks[start:start + BLACKLIST_NICKS_PAGE_SIZE]
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton('➕ Добавить ник', callback_data=f'{CB_BL_NICK_ADD}:{page}'))
    for offset, nick in enumerate(chunk):
        idx = start + offset
        shown = str(nick)
        if len(shown) > 42:
            shown = shown[:39] + '…'
        kb.row(InlineKeyboardButton(f'❌ {shown}', callback_data=f'{CB_BL_NICK_DEL}:{idx}:{page}'))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton('⬅️ Назад', callback_data=f'{CB_BL_NICK_PAGE}:{page - 1}'))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton('Далее ➡️', callback_data=f'{CB_BL_NICK_PAGE}:{page + 1}'))
    if nav:
        kb.row(*nav)
    kb.row(InlineKeyboardButton('◀️ Назад в чёрный список', callback_data=CB_BL))
    return kb

def open_blacklist_nicks(cardinal: 'Cardinal', call, page: int=0, notice: str=''):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    chat_id = call.message.chat.id
    data = load_data()
    cfg = _get_cfg(data)
    page, _ = _clamp_blacklist_nick_page(len(cfg.get('blacklist_nicks') or []), page)
    _safe_edit(bot, chat_id, _mid(call.message), _blacklist_nicks_text(chat_id, page, notice), _blacklist_nicks_kb(chat_id, page))

def start_blacklist_nicks_edit(cardinal: 'Cardinal', call):
    open_blacklist_nicks(cardinal, call, 0)

def start_blacklist_nick_add(cardinal: 'Cardinal', call, page: int=0):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    chat_id = call.message.chat.id
    _fsm[chat_id] = {'mode': 'blacklist_nick_add', 'step': 'nick', 'page': max(0, int(page)), 'panel_chat_id': chat_id, 'panel_msg_id': _mid(call.message), 'return': CB_BL_NICKS}
    _safe_edit(bot, chat_id, _mid(call.message), '➕ <b>Добавление ника в чёрный список</b>\n\nОтправьте <b>один</b> ник одним сообщением.\nМожно написать с символом <code>@</code> или без него.\n\nПример: <code>badbuyer</code>', _cancel_kb(CB_BL_NICKS))

def delete_blacklist_nick(cardinal: 'Cardinal', call, idx: int, page: int=0):
    bot = cardinal.telegram.bot
    chat_id = call.message.chat.id
    data = load_data()
    cfg = _get_cfg(data)
    nicks = list(cfg.get('blacklist_nicks') or [])
    if idx < 0 or idx >= len(nicks):
        _answer_cbq(bot, call, 'Ник уже удалён или список изменился.', alert=True)
        open_blacklist_nicks(cardinal, call, page)
        return
    removed = str(nicks.pop(idx))
    cfg['blacklist_nicks'] = nicks
    data['global'] = cfg
    save_data(data)
    _log_event(str(chat_id), 'BLACKLIST', f'Ник удалён из ЧС: {removed}', nick=removed)
    _answer_cbq(bot, call, f'Ник {removed} удалён.')
    page, _ = _clamp_blacklist_nick_page(len(nicks), page)
    _safe_edit(bot, chat_id, _mid(call.message), _blacklist_nicks_text(chat_id, page, f'✅ Ник <code>{escape(removed)}</code> удалён.'), _blacklist_nicks_kb(chat_id, page))

def start_blacklist_text_edit(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    data = load_data()
    cfg = _get_cfg(data)
    tpl = str(cfg.get('blacklist_text') or _default_cfg()['blacklist_text'])
    _fsm[chat_id] = {'mode': 'blacklist_text', 'panel_chat_id': chat_id, 'panel_msg_id': msg_id, 'return': CB_BL}
    _safe_edit(bot, chat_id, msg_id, f'💬 <b>Текст ответа для чёрного списка</b>\n\nТекущий текст:\n<code>{escape(tpl)}</code>\n\nПлейсхолдеры:\n• <code>{{nick}}</code> — ник покупателя\n• <code>{{buyer_id}}</code> — ID покупателя/чата\n• <code>{{matched_nick}}</code> — ник из ЧС, который совпал\n• <code>{{name}}</code> — название SDA аккаунта\n• <code>{{command}}</code> — команда аккаунта\n\nОтправь новый текст одним сообщением.\nЧтобы вернуть стандартный текст — отправь <code>-</code>.\n', _cancel_kb(CB_BL))

def _blacklist_accounts_text(chat_id: int) -> str:
    data = load_data()
    cfg = _get_cfg(data)
    accounts = _get_accounts_for(chat_id, data)
    save_data(data)
    if not accounts:
        return '✅ <b>Аккаунты для чёрного списка</b>\n\n❌ SDA аккаунтов нет.'
    selected = set((str(x) for x in cfg.get('blacklist_account_ids') or []))
    lines = []
    for i, acc in enumerate(accounts, start=1):
        acc_id = str(acc.get('account_id') or '')
        mark = '✅' if acc_id in selected else '⬜️'
        name = str(acc.get('name') or f'Аккаунт {i}')
        cmd = _normalize_cmd(str(acc.get('command') or ''))
        lines.append(f'{mark} {i}) <b>{escape(name)}</b>\n   💬 <code>{escape(cmd)}</code>')
    return '✅ <b>Аккаунты для чёрного списка</b>\n\nОтмеченные аккаунты будут проверяться, если режим применения = <b>выбранные аккаунты</b>.\n\n' + '\n\n'.join(lines)

def _blacklist_accounts_kb(chat_id: int) -> InlineKeyboardMarkup:
    data = load_data()
    cfg = _get_cfg(data)
    accounts = _get_accounts_for(chat_id, data)
    save_data(data)
    selected = set((str(x) for x in cfg.get('blacklist_account_ids') or []))
    kb = InlineKeyboardMarkup()
    for idx, acc in enumerate(accounts):
        acc_id = str(acc.get('account_id') or '')
        if not acc_id:
            continue
        name = str(acc.get('name') or f'Аккаунт {idx + 1}')
        mark = '✅' if acc_id in selected else '⬜️'
        kb.row(InlineKeyboardButton(f'{mark} {name}', callback_data=f'{CB_BL_ACC_TOGGLE}:{acc_id}'))
    kb.row(InlineKeyboardButton('◀️ Назад', callback_data=CB_BL))
    return kb

def open_blacklist_accounts(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    _safe_edit(bot, chat_id, msg_id, _blacklist_accounts_text(chat_id), _blacklist_accounts_kb(chat_id))

def toggle_blacklist_account(cardinal: 'Cardinal', call, account_id: str):
    bot = cardinal.telegram.bot
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    data = load_data()
    cfg = _get_cfg(data)
    accounts = _get_accounts_for(chat_id, data)
    valid_ids = {str(acc.get('account_id') or '') for acc in accounts}
    account_id = str(account_id or '').strip()
    if account_id not in valid_ids:
        _answer_cbq(bot, call, 'Аккаунт не найден.', alert=True)
        _safe_edit(bot, chat_id, msg_id, _blacklist_accounts_text(chat_id), _blacklist_accounts_kb(chat_id))
        return
    selected = set((str(x) for x in cfg.get('blacklist_account_ids') or []))
    if account_id in selected:
        selected.remove(account_id)
        action = 'убран'
    else:
        selected.add(account_id)
        action = 'добавлен'
    cfg['blacklist_account_ids'] = list(selected)
    cfg['blacklist_scope'] = 'selected'
    data['global'] = cfg
    save_data(data)
    _answer_cbq(bot, call, f'Аккаунт {action}. Режим: выбранные аккаунты.')
    _safe_edit(bot, chat_id, msg_id, _blacklist_accounts_text(chat_id), _blacklist_accounts_kb(chat_id))

def _cancel_all_queue_timers():
    with _timer_lock:
        keys = list(_queue_timers.keys())
    for key in keys:
        _cancel_timer(key)

def _find_live_account_by_key(account_key: str):
    data = load_data()
    cfg = _get_cfg(data)
    for owner_uid, accounts in (data or {}).items():
        if owner_uid == 'global' or not isinstance(accounts, list):
            continue
        _ensure_account_ids(str(owner_uid), accounts)
        for acc in accounts:
            if isinstance(acc, dict) and _account_key(str(owner_uid), acc) == account_key:
                return (str(owner_uid), acc, cfg)
    return (None, None, cfg)

def _account_queue_effective(acc: dict, cfg: dict) -> bool:
    return bool(cfg.get('plugin_enabled', True)) and bool(cfg.get('queue_enabled', True)) and bool(acc.get('enabled', True)) and bool(acc.get('queue_enabled', True))

def _account_command_notifications_effective(acc: dict, cfg: dict) -> bool:
    return bool(cfg.get('plugin_enabled', True)) and bool(cfg.get('command_notifications_enabled', True)) and bool(acc.get('command_notifications_enabled', True))

def _reschedule_available_queues(cardinal: 'Cardinal'):
    if not _plugin_enabled() or not _queue_enabled():
        return
    q = load_queue()
    _cleanup_queue_state(q)
    save_queue(q)
    for account_key, st in q.items():
        if not isinstance(st, dict) or not st.get('queue'):
            continue
        _, acc, cfg = _find_live_account_by_key(account_key)
        if acc is not None and _account_queue_effective(acc, cfg):
            _schedule_queue_processing(cardinal, account_key, _seconds_to_next_slot())

def toggle_plugin(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    new_state = _toggle_plugin_enabled()
    if new_state:
        _reschedule_available_queues(cardinal)
    else:
        _cancel_all_queue_timers()
    _log_event(str(call.message.chat.id), 'START' if new_state else 'STOP', f"Плагин {('включён' if new_state else 'выключен')}")
    _answer_cbq(bot, call, f"Плагин {('включён' if new_state else 'выключен')}.")
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    _safe_edit(bot, chat_id, msg_id, _settings_text(chat_id), _settings_kb())

def toggle_queue(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    new_state = _toggle_queue_enabled()
    if new_state:
        _reschedule_available_queues(cardinal)
    else:
        _cancel_all_queue_timers()
    _answer_cbq(bot, call, f"Очередь {('включена' if new_state else 'выключена')}.")
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    _safe_edit(bot, chat_id, msg_id, _settings_text(chat_id), _settings_kb())

def toggle_command_notifications(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    new_state = _toggle_command_notifications_enabled()
    _answer_cbq(bot, call, f"Уведомления команд {('включены' if new_state else 'выключены')}.")
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    _safe_edit(bot, chat_id, msg_id, _settings_text(chat_id), _settings_kb())

def toggle_command_notifications_debug(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    new_state = _toggle_command_notifications_debug_enabled()
    _answer_cbq(bot, call, f"Логи фильтра {('включены' if new_state else 'выключены')}.")
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    _safe_edit(bot, chat_id, msg_id, _settings_text(chat_id), _settings_kb())

def toggle_template_mode(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    new_mode = _toggle_template_mode()
    _answer_cbq(bot, call, f'Режим текста: {_template_mode_label(new_mode)}.')
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    _safe_edit(bot, chat_id, msg_id, _settings_text(chat_id), _settings_kb())
ACCOUNT_LIST_PAGE_SIZE = 5

def _clamp_account_page(total: int, page: int, per_page: int=ACCOUNT_LIST_PAGE_SIZE) -> tuple[int, int]:
    total_pages = max(1, (max(0, int(total)) + per_page - 1) // per_page)
    page = max(0, min(int(page), total_pages - 1))
    return (page, total_pages)

def _list_text(chat_id: int, page: int=0) -> str:
    data = load_data()
    accounts = _get_accounts_for(chat_id, data)
    save_data(data)
    if not accounts:
        return '📜 <b>Список аккаунтов.</b>\n\nНажмите на аккаунт, если хотите его посмотреть или редактировать.\n\n❌ Аккаунтов пока нет.'
    page, total_pages = _clamp_account_page(len(accounts), page)
    return f'📜 <b>Список аккаунтов.</b>\n\nНажмите на аккаунт, если хотите его посмотреть или редактировать.\n\nАккаунтов: <b>{len(accounts)}</b>\nСтраница: <b>{page + 1}/{total_pages}</b>'

def _list_kb(chat_id: int, page: int=0) -> InlineKeyboardMarkup:
    data = load_data()
    accounts = _get_accounts_for(chat_id, data)
    save_data(data)
    page, total_pages = _clamp_account_page(len(accounts), page)
    start = page * ACCOUNT_LIST_PAGE_SIZE
    chunk = accounts[start:start + ACCOUNT_LIST_PAGE_SIZE]
    kb = InlineKeyboardMarkup()
    for offset, acc in enumerate(chunk):
        idx = start + offset
        account_id = str(acc.get('account_id') or _make_account_id(str(chat_id), acc, idx))
        name = str(acc.get('name') or f'Аккаунт {idx + 1}')
        command = _normalize_cmd(str(acc.get('command') or ''))
        enabled_mark = '✅' if bool(acc.get('enabled', True)) else '⛔'
        title = f'{enabled_mark} {name}'
        if command:
            title += f' · {command}'
        if len(title) > 58:
            title = title[:55] + '…'
        kb.row(InlineKeyboardButton(title, callback_data=f'{CB_ACCOUNT_OPEN}:{account_id}:{page}'))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton('⬅️ Назад', callback_data=f'{CB_LIST_PAGE}:{page - 1}'))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton('Далее ➡️', callback_data=f'{CB_LIST_PAGE}:{page + 1}'))
    if nav:
        kb.row(*nav)
    kb.row(InlineKeyboardButton('◀️ В настройки', callback_data=CB_SETTINGS))
    return kb

def _back_to_settings_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton('◀️ Назад', callback_data=CB_SETTINGS))
    return kb

def open_list(cardinal: 'Cardinal', call, page: int=0):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    data = load_data()
    accounts = _get_accounts_for(chat_id, data)
    save_data(data)
    page, _ = _clamp_account_page(len(accounts), page)
    _safe_edit(bot, chat_id, msg_id, _list_text(chat_id, page), _list_kb(chat_id, page))

def _parse_account_callback(data: str, prefix: str) -> tuple[str, int]:
    raw = str(data or '')
    expected = f'{prefix}:'
    if not raw.startswith(expected):
        return ('', 0)
    payload = raw[len(expected):]
    parts = payload.split(':', 1)
    account_id = str(parts[0] or '').strip()
    try:
        page = int(parts[1]) if len(parts) > 1 else 0
    except (TypeError, ValueError):
        page = 0
    return (account_id, max(0, page))

def _get_account_context(chat_id: int, account_id: str):
    data = load_data()
    cfg = _get_cfg(data)
    accounts = _get_accounts_for(chat_id, data)
    idx = _find_account_index(accounts, account_id)
    save_data(data)
    return (data, cfg, accounts, idx)

def _account_detail_text(chat_id: int, account_id: str, notice: str='') -> str:
    data, cfg, accounts, idx = _get_account_context(chat_id, account_id)
    if idx < 0:
        return '❌ Аккаунт не найден. Вернитесь к списку и выберите его заново.'
    acc = accounts[idx]
    name = str(acc.get('name') or f'Аккаунт {idx + 1}')
    command = _normalize_cmd(str(acc.get('command') or ''))
    custom_template = str(acc.get('template') or '').strip()
    template_type = 'Кастомный' if custom_template else 'Общий'
    active_template = custom_template or str(cfg.get('template') or _default_cfg()['template'])
    preview = active_template if len(active_template) <= 500 else active_template[:497] + '…'
    enabled_state = 'ВКЛ' if bool(acc.get('enabled', True)) else 'ВЫКЛ'
    account_queue_state = 'ВКЛ' if bool(acc.get('queue_enabled', True)) else 'ВЫКЛ'
    effective_queue_state = 'ВКЛ' if _account_queue_effective(acc, cfg) else 'ВЫКЛ'
    account_notify_state = 'ВКЛ' if bool(acc.get('command_notifications_enabled', True)) else 'ВЫКЛ'
    effective_notify_state = 'ВКЛ' if _account_command_notifications_effective(acc, cfg) else 'ВЫКЛ'
    prefix = f'{notice}\n\n' if notice else ''
    return prefix + '👤 <b>Аккаунт Steam Guard</b>\n\n' + f'🏷 Название: <b>{escape(name)}</b>\n' + f'⚡ Выдача кодов: <b>{enabled_state}</b>\n' + f'⏳ Очередь аккаунта: <b>{account_queue_state}</b> (фактически: <b>{effective_queue_state}</b>)\n' + f'🔔 Уведомления команд: <b>{account_notify_state}</b> (фактически: <b>{effective_notify_state}</b>)\n' + f"💬 Команда: <code>{escape(command or '—')}</code>\n" + f'🔢 Лимит: <code>{escape(_limit_text(acc))}</code>\n' + f'📝 Тип текста: <b>{escape(template_type)}</b>\n' + f"🔐 shared_secret: <code>{escape(_mask_secret(str(acc.get('shared_secret') or '')))}</code>\n\n" + '📨 <b>Текущий текст ответа:</b>\n' + f"<code>{escape(preview or '—')}</code>\n\n" + 'Выберите, что хотите изменить:'

def _account_edit_cancel_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton('❌ Отменить', callback_data=CB_CANCEL), InlineKeyboardButton('◀️ Назад к аккаунту', callback_data=CB_CANCEL))
    return kb

def _account_detail_kb(account_id: str, page: int, chat_id: Optional[int]=None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    enabled_state = 'ВКЛ'
    queue_state = 'ВКЛ'
    notify_state = 'ВКЛ'
    if chat_id is not None:
        _, _, accounts, idx = _get_account_context(chat_id, account_id)
        if idx >= 0:
            enabled_state = 'ВКЛ' if bool(accounts[idx].get('enabled', True)) else 'ВЫКЛ'
            queue_state = 'ВКЛ' if bool(accounts[idx].get('queue_enabled', True)) else 'ВЫКЛ'
            notify_state = 'ВКЛ' if bool(accounts[idx].get('command_notifications_enabled', True)) else 'ВЫКЛ'
    kb.row(InlineKeyboardButton(f'⚡ Выдача кодов: {enabled_state}', callback_data=f'{CB_ACCOUNT_TOGGLE_ENABLED}:{account_id}:{page}'))
    kb.row(InlineKeyboardButton(f'⏳ Очередь аккаунта: {queue_state}', callback_data=f'{CB_ACCOUNT_TOGGLE_QUEUE}:{account_id}:{page}'))
    kb.row(InlineKeyboardButton(f'🔔 Уведомления команд: {notify_state}', callback_data=f'{CB_ACCOUNT_TOGGLE_NOTIFY}:{account_id}:{page}'))
    kb.row(InlineKeyboardButton('💬 Изменить команду', callback_data=f'{CB_ACCOUNT_EDIT_COMMAND}:{account_id}:{page}'))
    kb.row(InlineKeyboardButton('📝 Общий / кастомный текст', callback_data=f'{CB_ACCOUNT_TEXT_MENU}:{account_id}:{page}'))
    kb.row(InlineKeyboardButton('🔐 Заменить secret / maFile', callback_data=f'{CB_ACCOUNT_EDIT_SECRET}:{account_id}:{page}'))
    kb.row(InlineKeyboardButton('🔢 Изменить лимит', callback_data=f'{CB_ACCOUNT_EDIT_LIMIT}:{account_id}:{page}'))
    kb.row(InlineKeyboardButton('◀️ К списку аккаунтов', callback_data=f'{CB_LIST_PAGE}:{page}'))
    return kb

def _show_account_detail_panel(bot, chat_id: int, msg_id: int, account_id: str, page: int, notice: str=''):
    data, _, accounts, idx = _get_account_context(chat_id, account_id)
    if idx < 0:
        _safe_edit(bot, chat_id, msg_id, '❌ Аккаунт не найден.', _list_kb(chat_id, page))
        return
    _safe_edit(bot, chat_id, msg_id, _account_detail_text(chat_id, account_id, notice), _account_detail_kb(account_id, page, chat_id))

def open_account_detail(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    account_id, page = _parse_account_callback(call.data, CB_ACCOUNT_OPEN)
    _show_account_detail_panel(bot, call.message.chat.id, _mid(call.message), account_id, page)

def _clear_account_pending_queue(owner_uid: str, acc: dict) -> int:
    account_key = _account_key(str(owner_uid), acc)
    removed = 0
    with _queue_lock:
        q = load_queue()
        st = q.get(account_key)
        if isinstance(st, dict):
            queue_arr = st.get('queue')
            if isinstance(queue_arr, list):
                removed = len(queue_arr)
            st['queue'] = []
            q[account_key] = st
            save_queue(q)
    _cancel_timer(account_key)
    return removed

def toggle_account_enabled(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    account_id, page = _parse_account_callback(call.data, CB_ACCOUNT_TOGGLE_ENABLED)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    data, _, accounts, idx = _get_account_context(chat_id, account_id)
    if idx < 0:
        _answer_cbq(bot, call, 'Аккаунт не найден.', alert=True)
        _show_account_detail_panel(bot, chat_id, msg_id, account_id, page)
        return
    accounts[idx]['enabled'] = not bool(accounts[idx].get('enabled', True))
    new_state = bool(accounts[idx]['enabled'])
    _set_accounts_for(chat_id, data, accounts)
    _get_cfg(data)
    save_data(data)
    removed = 0
    if not new_state:
        removed = _clear_account_pending_queue(str(chat_id), accounts[idx])
    _answer_cbq(bot, call, f"Выдача кодов {('включена' if new_state else 'выключена')}.")
    notice = f"✅ Выдача кодов {('включена' if new_state else 'выключена')}."
    if removed:
        notice += f' Удалено из очереди: {removed}.'
    _show_account_detail_panel(bot, chat_id, msg_id, account_id, page, notice)

def toggle_account_queue(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    account_id, page = _parse_account_callback(call.data, CB_ACCOUNT_TOGGLE_QUEUE)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    data, _, accounts, idx = _get_account_context(chat_id, account_id)
    if idx < 0:
        _answer_cbq(bot, call, 'Аккаунт не найден.', alert=True)
        _show_account_detail_panel(bot, chat_id, msg_id, account_id, page)
        return
    accounts[idx]['queue_enabled'] = not bool(accounts[idx].get('queue_enabled', True))
    new_state = bool(accounts[idx]['queue_enabled'])
    _set_accounts_for(chat_id, data, accounts)
    _get_cfg(data)
    save_data(data)
    removed = 0
    if not new_state:
        removed = _clear_account_pending_queue(str(chat_id), accounts[idx])
    _answer_cbq(bot, call, f"Очередь аккаунта {('включена' if new_state else 'выключена')}.")
    notice = f"✅ Очередь аккаунта {('включена' if new_state else 'выключена')}."
    if removed:
        notice += f' Удалено ожидающих запросов: {removed}.'
    _show_account_detail_panel(bot, chat_id, msg_id, account_id, page, notice)

def toggle_account_notifications(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    account_id, page = _parse_account_callback(call.data, CB_ACCOUNT_TOGGLE_NOTIFY)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    data, _, accounts, idx = _get_account_context(chat_id, account_id)
    if idx < 0:
        _answer_cbq(bot, call, 'Аккаунт не найден.', alert=True)
        _show_account_detail_panel(bot, chat_id, msg_id, account_id, page)
        return
    accounts[idx]['command_notifications_enabled'] = not bool(accounts[idx].get('command_notifications_enabled', True))
    new_state = bool(accounts[idx]['command_notifications_enabled'])
    _set_accounts_for(chat_id, data, accounts)
    _get_cfg(data)
    save_data(data)
    _answer_cbq(bot, call, f"Уведомления команд аккаунта {('включены' if new_state else 'выключены')}.")
    _show_account_detail_panel(bot, chat_id, msg_id, account_id, page, f"✅ Уведомления команд аккаунта {('включены' if new_state else 'выключены')}.")

def _account_text_menu_text(chat_id: int, account_id: str) -> str:
    _, cfg, accounts, idx = _get_account_context(chat_id, account_id)
    if idx < 0:
        return '❌ Аккаунт не найден.'
    acc = accounts[idx]
    custom = str(acc.get('template') or '').strip()
    current_type = 'Кастомный' if custom else 'Общий'
    current = custom or str(cfg.get('template') or _default_cfg()['template'])
    preview = current if len(current) <= 600 else current[:597] + '…'
    return f'📝 <b>Текст ответа аккаунта</b>\n\nСейчас используется: <b>{escape(current_type)}</b> текст.\n\nТекущий текст:\n<code>{escape(preview)}</code>\n\nВыберите общий текст или задайте отдельный кастомный текст для этого аккаунта.'

def _account_text_menu_kb(account_id: str, page: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton('🌐 Использовать общий текст', callback_data=f'{CB_ACCOUNT_TEXT_GLOBAL}:{account_id}:{page}'))
    kb.row(InlineKeyboardButton('✏️ Задать кастомный текст', callback_data=f'{CB_ACCOUNT_TEXT_CUSTOM}:{account_id}:{page}'))
    kb.row(InlineKeyboardButton('◀️ Назад к аккаунту', callback_data=f'{CB_ACCOUNT_OPEN}:{account_id}:{page}'))
    return kb

def open_account_text_menu(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    account_id, page = _parse_account_callback(call.data, CB_ACCOUNT_TEXT_MENU)
    _safe_edit(bot, call.message.chat.id, _mid(call.message), _account_text_menu_text(call.message.chat.id, account_id), _account_text_menu_kb(account_id, page))

def _drop_account_queue(owner_uid: str, old_acc: dict):
    try:
        key = _account_key(str(owner_uid), old_acc)
        q = load_queue()
        if key in q:
            q.pop(key, None)
            save_queue(q)
        _cancel_timer(key)
    except Exception as e:
        logger.warning(f'{PREFIX} account queue cleanup failed: {e}')

def _save_account_record(chat_id: int, data: dict, accounts: List[dict], idx: int, old_acc: dict):
    _set_accounts_for(chat_id, data, accounts)
    _get_cfg(data)
    save_data(data)
    _drop_account_queue(str(chat_id), old_acc)

def start_account_command_edit(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    account_id, page = _parse_account_callback(call.data, CB_ACCOUNT_EDIT_COMMAND)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    _, _, accounts, idx = _get_account_context(chat_id, account_id)
    if idx < 0:
        _show_account_detail_panel(bot, chat_id, msg_id, account_id, page)
        return
    _fsm[chat_id] = {'mode': 'account_edit', 'step': 'command', 'account_id': account_id, 'page': page, 'panel_chat_id': chat_id, 'panel_msg_id': msg_id, 'return': 'account_detail'}
    current = _normalize_cmd(str(accounts[idx].get('command') or ''))
    _safe_edit(bot, chat_id, msg_id, f'💬 <b>Изменение команды</b>\n\nТекущая команда: <code>{escape(current)}</code>\n\nОтправьте новую команду одним сообщением.\nНапример: <code>!code_tinechelovec</code>\n\n', _account_edit_cancel_kb())

def use_account_global_text(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    account_id, page = _parse_account_callback(call.data, CB_ACCOUNT_TEXT_GLOBAL)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    data, _, accounts, idx = _get_account_context(chat_id, account_id)
    if idx < 0:
        _answer_cbq(bot, call, 'Аккаунт не найден.', alert=True)
        _show_account_detail_panel(bot, chat_id, msg_id, account_id, page)
        return
    old_acc = dict(accounts[idx])
    accounts[idx]['template'] = ''
    _save_account_record(chat_id, data, accounts, idx, old_acc)
    _answer_cbq(bot, call, 'Выбран общий текст.')
    _show_account_detail_panel(bot, chat_id, msg_id, account_id, page, '✅ Теперь аккаунт использует общий текст.')

def start_account_custom_text_edit(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    account_id, page = _parse_account_callback(call.data, CB_ACCOUNT_TEXT_CUSTOM)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    _, _, accounts, idx = _get_account_context(chat_id, account_id)
    if idx < 0:
        _show_account_detail_panel(bot, chat_id, msg_id, account_id, page)
        return
    _fsm[chat_id] = {'mode': 'account_edit', 'step': 'template', 'account_id': account_id, 'page': page, 'panel_chat_id': chat_id, 'panel_msg_id': msg_id, 'return': 'account_detail'}
    _safe_edit(bot, chat_id, msg_id, '✏️ <b>Кастомный текст аккаунта</b>\n\nОтправьте новый текст одним сообщением.\n\nДоступные плейсхолдеры:\n• <code>{code}</code> — код\n• <code>{name}</code> — название аккаунта\n• <code>{command}</code> — команда\n• <code>{left}</code> — осталось запросов\n• <code>{total}</code> — общий лимит или ∞\n• <code>{limit_text}</code> — лимит текстом\n\nПример:\n<code>✅ Ваш код: {code}\n📊 Осталось: {left}/{total}</code>\n\n', _account_edit_cancel_kb())

def start_account_secret_edit(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    account_id, page = _parse_account_callback(call.data, CB_ACCOUNT_EDIT_SECRET)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    _, _, accounts, idx = _get_account_context(chat_id, account_id)
    if idx < 0:
        _show_account_detail_panel(bot, chat_id, msg_id, account_id, page)
        return
    _fsm[chat_id] = {'mode': 'account_edit', 'step': 'secret', 'account_id': account_id, 'page': page, 'panel_chat_id': chat_id, 'panel_msg_id': msg_id, 'return': 'account_detail'}
    _safe_edit(bot, chat_id, msg_id, '🔐 <b>Замена shared_secret</b>\n\nОтправьте один из вариантов:\n• новый <code>shared_secret</code> текстом;\n• файл <b>.maFile</b> — бот сам извлечёт из него secret.\n\nНазвание аккаунта и команда при загрузке maFile не изменятся.\n', _account_edit_cancel_kb())

def start_account_limit_edit(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    account_id, page = _parse_account_callback(call.data, CB_ACCOUNT_EDIT_LIMIT)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    _, _, accounts, idx = _get_account_context(chat_id, account_id)
    if idx < 0:
        _show_account_detail_panel(bot, chat_id, msg_id, account_id, page)
        return
    _fsm[chat_id] = {'mode': 'account_edit', 'step': 'limit', 'account_id': account_id, 'page': page, 'panel_chat_id': chat_id, 'panel_msg_id': msg_id, 'return': 'account_detail'}
    _safe_edit(bot, chat_id, msg_id, f'🔢 <b>Изменение лимита</b>\n\nТекущий лимит: <code>{escape(_limit_text(accounts[idx]))}</code>\n\nОтправьте:\n• число больше 0 — новый лимит;\n• <code>-</code> — без ограничений.\n\n', _account_edit_cancel_kb())

def _account_edit_context(chat_id: int, st: dict):
    account_id = str(st.get('account_id') or '')
    data = load_data()
    cfg = _get_cfg(data)
    accounts = _get_accounts_for(chat_id, data)
    idx = _find_account_index(accounts, account_id)
    return (account_id, data, cfg, accounts, idx)

def _finish_account_edit(bot, chat_id: int, panel_msg_id: int, account_id: str, page: int, notice: str):
    _fsm.pop(chat_id, None)
    _show_account_detail_panel(bot, chat_id, panel_msg_id, account_id, page, notice)

def _handle_account_edit_document(message: Message, cardinal: 'Cardinal', st: dict):
    bot = cardinal.telegram.bot
    chat_id = message.chat.id
    panel_msg_id = int(st.get('panel_msg_id') or 0)
    page = int(st.get('page') or 0)
    account_id, data, _, accounts, idx = _account_edit_context(chat_id, st)
    if idx < 0:
        _finish_account_edit(bot, chat_id, panel_msg_id, account_id, page, '❌ Аккаунт не найден.')
        return
    try:
        mafile = _download_mafile(message, bot)
    except ValueError as e:
        _safe_edit(bot, chat_id, panel_msg_id, f'❌ <b>Не удалось обработать maFile</b>\n\n{escape(str(e))}\n\nОтправьте корректный .maFile или shared_secret текстом.', _account_edit_cancel_kb())
        return
    except Exception as e:
        logger.exception(f'{PREFIX} account maFile edit error: {e}')
        _safe_edit(bot, chat_id, panel_msg_id, '❌ Не удалось скачать или прочитать maFile.', _account_edit_cancel_kb())
        return
    old_acc = dict(accounts[idx])
    accounts[idx]['shared_secret'] = str(mafile['shared_secret'])
    _save_account_record(chat_id, data, accounts, idx, old_acc)
    _finish_account_edit(bot, chat_id, panel_msg_id, account_id, page, '✅ shared_secret заменён из maFile.')

def _handle_account_edit_text(text: str, cardinal: 'Cardinal', chat_id: int, panel_msg_id: int, st: dict):
    bot = cardinal.telegram.bot
    step = str(st.get('step') or '')
    page = int(st.get('page') or 0)
    account_id, data, cfg, accounts, idx = _account_edit_context(chat_id, st)
    if idx < 0:
        _finish_account_edit(bot, chat_id, panel_msg_id, account_id, page, '❌ Аккаунт не найден.')
        return
    old_acc = dict(accounts[idx])
    if step == 'command':
        cmd = _normalize_cmd(text)
        if not cmd:
            _safe_edit(bot, chat_id, panel_msg_id, '❌ Команда пустая. Введите её ещё раз.', _account_edit_cancel_kb())
            return
        reserved = {'sda_menu', '/sda_menu'}
        if cmd in reserved or cmd.lstrip('/') in reserved:
            _safe_edit(bot, chat_id, panel_msg_id, '❌ Эта команда зарезервирована. Введите другую.', _account_edit_cancel_kb())
            return
        for other_idx, other in enumerate(accounts):
            if other_idx != idx and _normalize_cmd(str(other.get('command') or '')) == cmd:
                _safe_edit(bot, chat_id, panel_msg_id, '❌ Такая команда уже используется другим аккаунтом.', _account_edit_cancel_kb())
                return
        accounts[idx]['command'] = cmd
        _save_account_record(chat_id, data, accounts, idx, old_acc)
        _finish_account_edit(bot, chat_id, panel_msg_id, account_id, page, f'✅ Команда изменена на <code>{escape(cmd)}</code>.')
        return
    if step == 'template':
        template = text.strip()
        if not template:
            _safe_edit(bot, chat_id, panel_msg_id, '❌ Текст не может быть пустым.', _account_edit_cancel_kb())
            return
        accounts[idx]['template'] = template
        cfg['template_mode'] = 'custom'
        data['global'] = cfg
        _save_account_record(chat_id, data, accounts, idx, old_acc)
        _finish_account_edit(bot, chat_id, panel_msg_id, account_id, page, '✅ Кастомный текст сохранён.')
        return
    if step == 'secret':
        secret = text.strip()
        if not generate_steam_guard_code(secret):
            _safe_edit(bot, chat_id, panel_msg_id, '❌ <b>Невалидный shared_secret</b>.\n\nОтправьте корректный secret текстом или файл .maFile.', _account_edit_cancel_kb())
            return
        accounts[idx]['shared_secret'] = secret
        _save_account_record(chat_id, data, accounts, idx, old_acc)
        _finish_account_edit(bot, chat_id, panel_msg_id, account_id, page, '✅ shared_secret заменён.')
        return
    if step == 'limit':
        raw = text.strip()
        if raw == '-':
            accounts[idx]['limit'] = None
            accounts[idx]['period_hours'] = None
            _save_account_record(chat_id, data, accounts, idx, old_acc)
            _finish_account_edit(bot, chat_id, panel_msg_id, account_id, page, '✅ Установлен лимит без ограничений.')
            return
        try:
            limit = int(raw)
            if limit <= 0:
                raise ValueError
        except ValueError:
            _safe_edit(bot, chat_id, panel_msg_id, '❌ Введите число больше 0 или <code>-</code>.', _account_edit_cancel_kb())
            return
        st['pending_limit'] = limit
        st['step'] = 'period'
        _safe_edit(bot, chat_id, panel_msg_id, f'⏱ <b>Период лимита</b>\n\nНовый лимит: <b>{limit}</b>.\n\nОтправьте период в часах.\n• <code>24</code> — лимит обновляется каждые 24 часа;\n• <code>0</code> или <code>-</code> — лимит действует навсегда для покупателя.', _account_edit_cancel_kb())
        return
    if step == 'period':
        try:
            limit = int(st.get('pending_limit'))
            if limit <= 0:
                raise ValueError
        except (TypeError, ValueError):
            st['step'] = 'limit'
            _safe_edit(bot, chat_id, panel_msg_id, '⚠️ Лимит не сохранился. Введите его заново.', _account_edit_cancel_kb())
            return
        raw = text.strip()
        if raw in {'-', '0'}:
            hours = None
        else:
            try:
                hours = int(raw)
                if hours <= 0:
                    raise ValueError
            except ValueError:
                _safe_edit(bot, chat_id, panel_msg_id, '❌ Введите число больше 0, либо <code>0</code> / <code>-</code>.', _account_edit_cancel_kb())
                return
        accounts[idx]['limit'] = limit
        accounts[idx]['period_hours'] = hours
        _save_account_record(chat_id, data, accounts, idx, old_acc)
        label = f'{limit} навсегда' if hours is None else f'{limit} за {hours}ч'
        _finish_account_edit(bot, chat_id, panel_msg_id, account_id, page, f'✅ Лимит изменён: <code>{escape(label)}</code>.')
        return
    _finish_account_edit(bot, chat_id, panel_msg_id, account_id, page, '⚠️ Неизвестный этап редактирования.')

def _del_menu_text(chat_id: int) -> str:
    data = load_data()
    accounts = _get_accounts_for(chat_id, data)
    save_data(data)
    if not accounts:
        return '🗑 <b>Удалить аккаунт</b>\n\n❌ Аккаунтов нет.'
    return '🗑 <b>Удалить аккаунт</b>\n\nВыбери аккаунт для удаления:'

def _del_menu_kb(chat_id: int) -> InlineKeyboardMarkup:
    data = load_data()
    accounts = _get_accounts_for(chat_id, data)
    save_data(data)
    kb = InlineKeyboardMarkup()
    for idx, acc in enumerate(accounts):
        title = str(acc.get('name') or f'Аккаунт {idx + 1}')
        cmd = _normalize_cmd(str(acc.get('command') or ''))
        kb.row(InlineKeyboardButton(f'🗑 {title} ({cmd})', callback_data=f'{CB_DEL_PICK}:{idx}'))
    kb.row(InlineKeyboardButton('◀️ Назад', callback_data=CB_SETTINGS))
    return kb

def open_del_menu(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    _safe_edit(bot, chat_id, msg_id, _del_menu_text(chat_id), _del_menu_kb(chat_id))

def _del_confirm_text(acc: dict) -> str:
    return f"🗑 <b>Подтверждение удаления</b>\n\nУдалить аккаунт:\n🏷 <b>{escape(str(acc.get('name', '')))}</b>\n💬 <code>{escape(_normalize_cmd(str(acc.get('command', ''))))}</code>\n\nЭто действие необратимо."

def _del_confirm_kb(idx: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton('✅ Да', callback_data=f'{CB_DEL_YES}:{idx}'), InlineKeyboardButton('❌ Нет', callback_data=CB_DEL_NO))
    kb.row(InlineKeyboardButton('◀️ Назад', callback_data=CB_DEL_MENU))
    return kb

def open_del_confirm(cardinal: 'Cardinal', call, idx: int):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    data = load_data()
    accounts = _get_accounts_for(chat_id, data)
    save_data(data)
    if idx < 0 or idx >= len(accounts):
        _safe_edit(bot, chat_id, msg_id, '❌ Аккаунт не найден.', _back_to_settings_kb())
        return
    _safe_edit(bot, chat_id, msg_id, _del_confirm_text(accounts[idx]), _del_confirm_kb(idx))

def del_yes(cardinal: 'Cardinal', call, idx: int):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    data = load_data()
    accounts = _get_accounts_for(chat_id, data)
    if idx < 0 or idx >= len(accounts):
        _safe_edit(bot, chat_id, msg_id, '❌ Аккаунт не найден.', _back_to_settings_kb())
        return
    removed = accounts.pop(idx)
    _set_accounts_for(chat_id, data, accounts)
    _get_cfg(data)
    save_data(data)
    _safe_edit(bot, chat_id, msg_id, f"✅ Аккаунт удалён: <b>{escape(str(removed.get('name', '')))}</b>", _settings_kb())

def del_no(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call, 'Отменено.')
    open_del_menu(cardinal, call)

def _logs_text(chat_id: int, page: int=0, per_page: int=8) -> str:
    owner_uid = str(chat_id)
    logs = load_logs()
    arr = logs.get(owner_uid)
    if not isinstance(arr, list) or not arr:
        return '🧾 <b>Диагностические логи</b>\n\n❌ Пока пусто.'
    arr = list(reversed(arr))
    total_pages = max(1, (len(arr) + per_page - 1) // per_page)
    page = max(0, min(int(page), total_pages - 1))
    chunk = arr[page * per_page:(page + 1) * per_page]
    icons = {'START': '🚀', 'STOP': '🛑', 'UI_CLICK': '👆', 'SCREEN': '🧭', 'COMMAND': '💬', 'CODE': '✅', 'QUEUE': '⏳', 'LIMIT': '🔢', 'BUSY': '⌛', 'BLACKLIST': '🚫', 'CONFIG': '📦', 'ERROR': '❌', 'DISABLED': '⛔', 'FSM_INPUT': '⌨️', 'ACTION': '⚙️', 'INFO': 'ℹ️'}
    lines = []
    for e in chunk:
        kind = str(e.get('type') or 'INFO').upper()
        icon = icons.get(kind, '•')
        ts = _fmt_dt(int(e.get('ts') or 0))
        msg = str(e.get('msg') or '—')
        details = []
        for key, label in (('name', 'аккаунт'), ('cmd', 'команда'), ('buyer', 'buyer'), ('nick', 'ник'), ('screen', 'экран'), ('where', 'модуль'), ('mode', 'режим'), ('step', 'шаг'), ('accounts', 'аккаунтов'), ('position', 'позиция'), ('callback', 'callback')):
            value = e.get(key)
            if value not in (None, ''):
                details.append(f'{label}: <code>{escape(str(value))}</code>')
        block = f'{icon} <code>{escape(ts)}</code> — <b>{escape(kind)}</b>\n{escape(msg)}'
        if details:
            block += '\n' + ' | '.join(details)
        lines.append(block)
    return f'🧾 <b>Диагностические логи</b>\n\nВсего событий: <b>{len(arr)}</b> | Версия: <code>{escape(VERSION)}</code>\nСтраница: <b>{page + 1}/{total_pages}</b>\n\n' + '\n\n'.join(lines)

def _logs_kb(chat_id: int, page: int, per_page: int=8) -> InlineKeyboardMarkup:
    logs = load_logs()
    arr = logs.get(str(chat_id))
    total = len(arr) if isinstance(arr, list) else 0
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(0, min(int(page), total_pages - 1))
    kb = InlineKeyboardMarkup()
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton('⬅️ Назад', callback_data=f'{CB_LOGS}:{page - 1}'))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton('Далее ➡️', callback_data=f'{CB_LOGS}:{page + 1}'))
    if nav:
        kb.row(*nav)
    kb.row(InlineKeyboardButton('🔄 Обновить', callback_data=f'{CB_LOGS}:{page}'))
    kb.row(InlineKeyboardButton('◀️ Назад в настройки', callback_data=CB_SETTINGS))
    return kb

def open_logs(cardinal: 'Cardinal', call, page: int):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    _safe_edit(bot, chat_id, msg_id, _logs_text(chat_id, page), _logs_kb(chat_id, page))

def _template_text(chat_id: int) -> str:
    data = load_data()
    cfg = _get_cfg(data)
    tpl = (cfg.get('template') or '').strip()
    return f"✏️ <b>Общее сообщение выдачи кода</b>\n\nТекущий общий шаблон:\n<code>{escape(tpl or '—')}</code>\n\nПлейсхолдеры:\n• <code>{{code}}</code> — код\n• <code>{{name}}</code> — название аккаунта\n• <code>{{command}}</code> — команда\n• <code>{{left}}</code> — осталось\n• <code>{{total}}</code> — всего/∞\n• <code>{{limit_text}}</code> — лимит текстом\n\nОтправь новый общий шаблон <b>одним сообщением</b>.\n"

def start_template_edit(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    _fsm[chat_id] = {'mode': 'template', 'panel_chat_id': chat_id, 'panel_msg_id': msg_id, 'return': CB_SETTINGS}
    _safe_edit(bot, chat_id, msg_id, _template_text(chat_id), _cancel_kb(CB_SETTINGS))

def _account_template_menu_text(chat_id: int) -> str:
    data = load_data()
    cfg = _get_cfg(data)
    accounts = _get_accounts_for(chat_id, data)
    save_data(data)
    if not accounts:
        return '🧩 <b>Кастомные тексты аккаунтов</b>\n\n❌ Аккаунтов нет.'
    mode_label = _template_mode_label(str(cfg.get('template_mode') or 'global'))
    lines = []
    for i, acc in enumerate(accounts, start=1):
        name = str(acc.get('name') or f'Аккаунт {i}')
        cmd = _normalize_cmd(str(acc.get('command') or ''))
        state = _account_template_state(acc)
        lines.append(f'{i}) 🏷 <b>{escape(name)}</b>\n   💬 <code>{escape(cmd)}</code>\n   📝 Текст: <code>{escape(state)}</code>')
    return f'🧩 <b>Кастомные тексты аккаунтов</b>\n\nТекущий режим: <b>{escape(mode_label)}</b>\nКастомные тексты реально используются только когда режим текста = <b>Кастомный</b>.\n\nВыбери аккаунт, для которого нужно настроить отдельный текст выдачи кода.\n\n' + '\n\n'.join(lines)

def _account_template_menu_kb(chat_id: int) -> InlineKeyboardMarkup:
    data = load_data()
    accounts = _get_accounts_for(chat_id, data)
    save_data(data)
    kb = InlineKeyboardMarkup()
    for idx, acc in enumerate(accounts):
        name = str(acc.get('name') or f'Аккаунт {idx + 1}')
        state = _account_template_state(acc)
        acc_id = str(acc.get('account_id') or _make_account_id(str(chat_id), acc, idx))
        kb.row(InlineKeyboardButton(f'📝 {name} ({state})', callback_data=f'{CB_ACCOUNT_TEMPLATE_PICK}:{acc_id}'))
    kb.row(InlineKeyboardButton('📝 Переключить общий/кастомный', callback_data=CB_TEMPLATE_MODE_TOGGLE))
    kb.row(InlineKeyboardButton('◀️ Назад', callback_data=CB_SETTINGS))
    return kb

def open_account_template_menu(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    _safe_edit(bot, chat_id, msg_id, _account_template_menu_text(chat_id), _account_template_menu_kb(chat_id))

def _account_template_edit_text(chat_id: int, account_id: str) -> str:
    data = load_data()
    cfg = _get_cfg(data)
    accounts = _get_accounts_for(chat_id, data)
    save_data(data)
    idx = _find_account_index(accounts, account_id)
    if idx < 0:
        return '❌ Аккаунт не найден. Вернись назад и выбери аккаунт заново.'
    acc = accounts[idx]
    name = str(acc.get('name') or f'Аккаунт {idx + 1}')
    cmd = _normalize_cmd(str(acc.get('command') or ''))
    acc_tpl = str(acc.get('template') or '').strip()
    global_tpl = str(cfg.get('template') or _default_cfg()['template']).strip()
    mode = str(cfg.get('template_mode') or 'global')
    if acc_tpl:
        current = acc_tpl
        state = 'свой шаблон'
    else:
        current = global_tpl
        state = 'общий шаблон'
    mode_note = 'будет использоваться' if mode == 'custom' else 'сохранится, но не будет использоваться, пока режим текста = Общий'
    return f"🧩 <b>Кастомный текст аккаунта</b>\n\nАккаунт: <b>{escape(name)}</b>\nКоманда: <code>{escape(cmd)}</code>\nСейчас у аккаунта: <b>{escape(state)}</b>\nРежим текста: <b>{escape(_template_mode_label(mode))}</b> — свой текст {escape(mode_note)}.\n\nТекущий текст:\n<code>{escape(current or '—')}</code>\n\nПлейсхолдеры:\n• <code>{{code}}</code> — код\n• <code>{{name}}</code> — название аккаунта\n• <code>{{command}}</code> — команда\n• <code>{{left}}</code> — осталось\n• <code>{{total}}</code> — всего/∞\n• <code>{{limit_text}}</code> — лимит текстом\n\nОтправь новый текст <b>одним сообщением</b>.\nЧтобы сбросить личный текст и использовать общий шаблон — отправь <code>-</code>.\n\n"

def start_account_template_edit(cardinal: 'Cardinal', call, account_id: str):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    data = load_data()
    accounts = _get_accounts_for(chat_id, data)
    save_data(data)
    idx = _find_account_index(accounts, account_id)
    if idx < 0:
        try:
            old_idx = int(str(account_id))
            if 0 <= old_idx < len(accounts):
                idx = old_idx
                account_id = str(accounts[idx].get('account_id') or _make_account_id(str(chat_id), accounts[idx], idx))
        except Exception:
            pass
    if idx < 0:
        _safe_edit(bot, chat_id, msg_id, '❌ Аккаунт не найден. Список обновлён — выбери аккаунт ещё раз.', _account_template_menu_kb(chat_id))
        return
    _fsm[chat_id] = {'mode': 'account_template', 'account_id': str(account_id), 'account_idx': idx, 'panel_chat_id': chat_id, 'panel_msg_id': msg_id, 'return': CB_ACCOUNT_TEMPLATE_MENU}
    _safe_edit(bot, chat_id, msg_id, _account_template_edit_text(chat_id, str(account_id)), _cancel_kb(CB_ACCOUNT_TEMPLATE_MENU))

def _fsm_cancel(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    chat_id = call.message.chat.id
    st = _fsm.get(chat_id) or {}
    ret = st.get('return') or CB_SETTINGS
    mode = st.get('mode')
    account_id = str(st.get('account_id') or '')
    page = int(st.get('page') or 0)
    _fsm.pop(chat_id, None)
    _answer_cbq(bot, call, 'Отменено.')
    if mode == 'account_edit' and account_id:
        _show_account_detail_panel(bot, chat_id, _mid(call.message), account_id, page)
    elif ret == CB_ACCOUNT_TEMPLATE_MENU:
        open_account_template_menu(cardinal, call)
    elif ret == CB_BL:
        open_blacklist(cardinal, call)
    elif ret == CB_BL_ACCS:
        open_blacklist_accounts(cardinal, call)
    elif ret == CB_BL_NICKS:
        open_blacklist_nicks(cardinal, call, int(st.get('page') or 0))
    elif ret == CB_CONFIG_MENU:
        open_config_menu(cardinal, call)
    elif ret == CB_UPDATE_PLUGIN:
        open_update_menu(cardinal, call)
    else:
        open_settings(cardinal, call)

def _start_add(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    chat_id = call.message.chat.id
    msg_id = _mid(call.message)
    _fsm[chat_id] = {'mode': 'add', 'step': 'secret', 'panel_chat_id': chat_id, 'panel_msg_id': msg_id, 'tmp': {}, 'return': CB_SETTINGS}
    _safe_edit(bot, chat_id, msg_id, '➕ <b>Добавление SDA аккаунта</b>\n\nШаг 1: отправь один из вариантов:\n• файл <b>.maFile</b> — бот сам достанет <code>shared_secret</code> и ник;\n• либо отправь <b>shared_secret</b> обычным текстом.\n\n', _cancel_kb(CB_SETTINGS))

def _restart_add(bot, chat_id: int, panel_msg_id: int):
    _fsm[chat_id] = {'mode': 'add', 'step': 'secret', 'panel_chat_id': chat_id, 'panel_msg_id': panel_msg_id, 'tmp': {}, 'return': CB_SETTINGS}
    _safe_edit(bot, chat_id, panel_msg_id, '⚠️ Похоже, состояние добавления сбилось. Начнём заново.\n\nОтправь файл <b>.maFile</b> или <b>shared_secret</b> обычным текстом.\n', _cancel_kb(CB_SETTINGS))

def _show_add_command_choice(bot, chat_id: int, panel_msg_id: int, st: dict, accounts: List[dict]):
    tmp = st.setdefault('tmp', {})
    command_nick = str(tmp.get('command_nick') or tmp.get('name') or 'account')
    suggested_command = _make_default_code_command(command_nick, accounts)
    tmp['suggested_command'] = suggested_command
    st['step'] = 'command_choice'
    source = str(tmp.get('source') or 'manual')
    if source == 'mafile':
        source_text = f"📄 Ник из maFile: <code>{escape(command_nick)}</code>\n🏷 Название аккаунта: <b>{escape(str(tmp.get('name') or command_nick))}</b>\n\n"
    else:
        source_text = 'Команда создаётся в формате <code>!code_ник</code>.\nПример: <code>!code_tinechelovec</code>\n\n'
    _safe_edit(bot, chat_id, panel_msg_id, '💬 <b>Создание команды для получения кода</b>\n\n' + source_text + f'По умолчанию будет создана команда:\n<code>{escape(suggested_command)}</code>\n\nИменно её покупатель будет писать в чате.\nМожно оставить этот вариант или создать свою команду.', _add_command_choice_kb(suggested_command))

def _show_add_limit_step(bot, chat_id: int, panel_msg_id: int, st: dict):
    st['step'] = 'limit'
    _safe_edit(bot, chat_id, panel_msg_id, '🔢 <b>Лимит запросов</b>\n\nСколько раз один покупатель сможет запросить код по этой команде?\n\nПримеры:\n• <code>5</code> — 5 запросов на покупателя\n• <code>-</code> — без ограничений', _cancel_kb(CB_SETTINGS))

def _add_use_auto_command(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    chat_id = call.message.chat.id
    panel_msg_id = _mid(call.message)
    st = _fsm.get(chat_id) or {}
    if st.get('mode') != 'add' or st.get('step') != 'command_choice':
        _answer_cbq(bot, call, 'Сценарий добавления уже завершён или сбился.', alert=True)
        return
    data = load_data()
    accounts = _get_accounts_for(chat_id, data)
    tmp = st.setdefault('tmp', {})
    command_nick = str(tmp.get('command_nick') or tmp.get('name') or 'account')
    command = _make_default_code_command(command_nick, accounts)
    tmp['suggested_command'] = command
    tmp['command'] = command
    _answer_cbq(bot, call, f'Выбрана команда {command}')
    _show_add_limit_step(bot, chat_id, panel_msg_id, st)

def _add_choose_custom_command(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    chat_id = call.message.chat.id
    panel_msg_id = _mid(call.message)
    st = _fsm.get(chat_id) or {}
    if st.get('mode') != 'add' or st.get('step') != 'command_choice':
        _answer_cbq(bot, call, 'Сценарий добавления уже завершён или сбился.', alert=True)
        return
    st['step'] = 'command'
    _answer_cbq(bot, call)
    _safe_edit(bot, chat_id, panel_msg_id, '✏️ <b>Своя команда</b>\n\nОтправь команду одним сообщением.\nРекомендуемый формат: <code>!code_ник</code>\nПример: <code>!code_tinechelovec</code>\n\n⚠️ Команда будет очищена от пробелов и невидимых символов.', _cancel_kb(CB_SETTINGS))

def _show_add_template_choice(bot, chat_id: int, panel_msg_id: int, st: dict):
    data = load_data()
    cfg = _get_cfg(data)
    global_tpl = str(cfg.get('template') or _default_cfg()['template']).strip()
    preview = global_tpl if len(global_tpl) <= 350 else global_tpl[:347] + '…'
    st['step'] = 'template_choice'
    _safe_edit(bot, chat_id, panel_msg_id, f'📝 <b>Текст сообщения с кодом</b>\n\nКакой текст использовать для этого аккаунта?\n\n🌐 <b>Общий текст</b> — будет использован текущий общий шаблон:\n<code>{escape(preview)}</code>\n\n✏️ <b>Кастомный текст</b> — после выбора бот попросит написать отдельный текст именно для этого аккаунта.', _add_template_choice_kb())

def _finalize_add_account(cardinal: 'Cardinal', chat_id: int, panel_msg_id: int, st: dict):
    bot = cardinal.telegram.bot
    tmp = st.setdefault('tmp', {})
    required = ('name', 'command', 'shared_secret', 'limit', 'period_hours', 'template', 'queue_enabled')
    if any((key not in tmp for key in required)):
        _restart_add(bot, chat_id, panel_msg_id)
        return
    data = load_data()
    accounts = _get_accounts_for(chat_id, data)
    acc = {'name': tmp['name'], 'command': tmp['command'], 'shared_secret': tmp['shared_secret'], 'limit': tmp['limit'], 'period_hours': tmp['period_hours'], 'template': str(tmp.get('template') or '').strip(), 'enabled': True, 'queue_enabled': bool(tmp.get('queue_enabled', True)), 'command_notifications_enabled': True}
    accounts.append(acc)
    _set_accounts_for(chat_id, data, accounts)
    cfg = _get_cfg(data)
    data['global'] = cfg
    save_data(data)
    if acc['limit'] is None:
        limit_text = 'без ограничений'
    elif acc['period_hours'] is None:
        limit_text = f"{acc['limit']} навсегда"
    else:
        limit_text = f"{acc['limit']} за {acc['period_hours']}ч"
    if acc['template']:
        template_label = 'кастомный'
        template_preview = acc['template'] if len(acc['template']) <= 300 else acc['template'][:297] + '…'
    else:
        template_label = 'общий'
        template_preview = str(cfg.get('template') or _default_cfg()['template']).strip()
        if len(template_preview) > 300:
            template_preview = template_preview[:297] + '…'
    queue_label = 'ВКЛ' if acc['queue_enabled'] else 'ВЫКЛ'
    _fsm.pop(chat_id, None)
    _safe_edit(bot, chat_id, panel_msg_id, f"✅ <b>Аккаунт добавлен</b>\n\n🏷 <b>{escape(str(acc['name']))}</b>\n💬 <code>{escape(str(acc['command']))}</code>\n🔢 <code>{escape(limit_text)}</code>\n⏳ Очередь: <b>{queue_label}</b>\n🔔 Уведомления команд: <b>ВКЛ</b>\n📝 Текст: <b>{escape(template_label)}</b>\n<code>{escape(template_preview)}</code>\n🔐 secret: <code>{escape(_mask_secret(str(acc['shared_secret'])))}</code>", _settings_kb())

def _add_use_global_template(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    chat_id = call.message.chat.id
    panel_msg_id = _mid(call.message)
    st = _fsm.get(chat_id) or {}
    if st.get('mode') != 'add' or st.get('step') != 'template_choice':
        _answer_cbq(bot, call, 'Сценарий добавления уже завершён или сбился.', alert=True)
        return
    st.setdefault('tmp', {})['template'] = ''
    _answer_cbq(bot, call, 'Выбран общий текст.')
    _show_add_queue_choice(bot, chat_id, panel_msg_id, st)

def _add_choose_custom_template(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    chat_id = call.message.chat.id
    panel_msg_id = _mid(call.message)
    st = _fsm.get(chat_id) or {}
    if st.get('mode') != 'add' or st.get('step') != 'template_choice':
        _answer_cbq(bot, call, 'Сценарий добавления уже завершён или сбился.', alert=True)
        return
    st['step'] = 'template_custom'
    _answer_cbq(bot, call)
    _safe_edit(bot, chat_id, panel_msg_id, '✏️ <b>Кастомный текст сообщения</b>\n\nНапиши текст, который покупатель будет получать вместе с кодом.\n\nДоступные плейсхолдеры:\n• <code>{code}</code> — Steam Guard код\n• <code>{name}</code> — название аккаунта\n• <code>{command}</code> — команда\n• <code>{left}</code> — сколько запросов осталось\n• <code>{total}</code> — общий лимит или ∞\n• <code>{limit_text}</code> — лимит текстом\n\nПример:\n<code>✅ Ваш код: {code}\n📊 Осталось: {left}/{total}</code>\n\n', _cancel_kb(CB_SETTINGS))

def _add_choose_queue(cardinal: 'Cardinal', call, enabled: bool):
    bot = cardinal.telegram.bot
    chat_id = call.message.chat.id
    panel_msg_id = _mid(call.message)
    st = _fsm.get(chat_id) or {}
    if st.get('mode') != 'add' or st.get('step') != 'queue_choice':
        _answer_cbq(bot, call, 'Сценарий добавления уже завершён или сбился.', alert=True)
        return
    st.setdefault('tmp', {})['queue_enabled'] = bool(enabled)
    _answer_cbq(bot, call, f"Очередь {('включена' if enabled else 'выключена')}.")
    _finalize_add_account(cardinal, chat_id, panel_msg_id, st)

def _handle_fsm(message: Message, cardinal: 'Cardinal'):
    chat_id = message.chat.id
    if chat_id not in _fsm:
        return
    st = _fsm.get(chat_id) or {}
    mode = st.get('mode')
    bot = cardinal.telegram.bot
    panel_msg_id = int(st.get('panel_msg_id') or 0)
    step = st.get('step')
    document = getattr(message, 'document', None)
    _log_event(str(chat_id), 'FSM_INPUT', f"Получен ввод: режим={mode}, шаг={step}, тип={('document' if document is not None else 'text')}", mode=str(mode or ''), step=str(step or ''))
    if mode == 'add' and step == 'secret' and (document is not None):
        try:
            mafile = _download_mafile(message, bot)
            tmp = st.setdefault('tmp', {})
            tmp['shared_secret'] = mafile['shared_secret']
            tmp['name'] = mafile['account_name']
            tmp['command_nick'] = mafile['account_name']
            tmp['source'] = 'mafile'
            data = load_data()
            accounts = _get_accounts_for(chat_id, data)
            _show_add_command_choice(bot, chat_id, panel_msg_id, st, accounts)
        except ValueError as e:
            if panel_msg_id:
                _safe_edit(bot, chat_id, panel_msg_id, f'❌ <b>Не удалось обработать maFile</b>\n\n{escape(str(e))}\n\nОтправь корректный файл <b>.maFile</b> или shared_secret обычным текстом.', _cancel_kb(CB_SETTINGS))
        except Exception as e:
            logger.exception(f'{PREFIX} maFile download error: {e}')
            if panel_msg_id:
                _safe_edit(bot, chat_id, panel_msg_id, '❌ Не удалось скачать или прочитать maFile. Попробуй отправить файл ещё раз.', _cancel_kb(CB_SETTINGS))
        finally:
            _try_delete(bot, chat_id, _mid(message))
        return
    if mode == 'account_edit' and step == 'secret' and (document is not None):
        try:
            _handle_account_edit_document(message, cardinal, st)
        finally:
            _try_delete(bot, chat_id, _mid(message))
        return
    if mode == 'config_import' and step == 'document' and (document is not None):
        try:
            _handle_config_import_document(message, cardinal, st)
        finally:
            _try_delete(bot, chat_id, _mid(message))
        return
    if mode == 'plugin_update_local' and step == 'document' and (document is not None):
        try:
            _handle_local_plugin_update_document(message, cardinal, st)
        finally:
            _try_delete(bot, chat_id, _mid(message))
        return
    text = (message.text or '').strip()
    _try_delete(bot, chat_id, _mid(message))
    if document is not None and (not text):
        if panel_msg_id:
            if mode == 'add' and step == 'secret':
                expected = 'файл .maFile или shared_secret'
            elif mode == 'config_import':
                expected = 'JSON-файл конфигурации'
            elif mode == 'plugin_update_local':
                expected = 'Python-файл плагина .py'
            else:
                expected = 'текстовое сообщение'
            kb = _account_edit_cancel_kb() if mode == 'account_edit' else _cancel_kb(st.get('return') or CB_SETTINGS)
            _safe_edit(bot, chat_id, panel_msg_id, f'❌ Сейчас ожидается {expected}.', kb)
        return
    if not text:
        return
    if text.startswith('/'):
        _fsm.pop(chat_id, None)
        if panel_msg_id:
            _safe_edit(bot, chat_id, panel_msg_id, '❌ Операция отменена.', _settings_kb())
        return
    if mode == 'config_import':
        if panel_msg_id:
            _safe_edit(bot, chat_id, panel_msg_id, '❌ Отправьте конфигурацию именно JSON-файлом.', _cancel_kb(CB_CONFIG_MENU))
        return
    if mode == 'plugin_update_local':
        if panel_msg_id:
            _safe_edit(bot, chat_id, panel_msg_id, '❌ Отправьте обновление именно Python-файлом <code>.py</code>.', _cancel_kb(CB_UPDATE_PLUGIN))
        return
    if mode == 'template':
        tpl = text.strip()
        data = load_data()
        cfg = _get_cfg(data)
        cfg['template'] = tpl
        _set_cfg(cfg)
        _fsm.pop(chat_id, None)
        if panel_msg_id:
            _safe_edit(bot, chat_id, panel_msg_id, '✅ Общий шаблон обновлён.', _settings_kb())
        return
    if mode == 'account_template':
        account_id = str(st.get('account_id') or '')
        data = load_data()
        accounts = _get_accounts_for(chat_id, data)
        idx = _find_account_index(accounts, account_id)
        if idx < 0:
            old_idx = int(st.get('account_idx') or -1)
            if 0 <= old_idx < len(accounts):
                idx = old_idx
        if idx < 0 and len(accounts) == 1:
            idx = 0
        if idx < 0 or idx >= len(accounts):
            _fsm.pop(chat_id, None)
            if panel_msg_id:
                _safe_edit(bot, chat_id, panel_msg_id, '❌ Аккаунт не найден. Открыл обновлённый список — выбери аккаунт ещё раз.', _account_template_menu_kb(chat_id))
            return
        if text.strip() == '-':
            accounts[idx].pop('template', None)
            result_text = '✅ Личный текст аккаунта сброшен. Теперь для него будет использоваться общий текст.'
        else:
            accounts[idx]['template'] = text.strip()
            result_text = '✅ Личный текст аккаунта обновлён. Режим текста переключён на «Кастомный».'
            cfg = _get_cfg(data)
            cfg['template_mode'] = 'custom'
            data['global'] = cfg
        _set_accounts_for(chat_id, data, accounts)
        _get_cfg(data)
        save_data(data)
        _fsm.pop(chat_id, None)
        if panel_msg_id:
            _safe_edit(bot, chat_id, panel_msg_id, result_text, _account_template_menu_kb(chat_id))
        return
    if mode == 'account_edit':
        _handle_account_edit_text(text, cardinal, chat_id, panel_msg_id, st)
        return
    if mode == 'blacklist_nick_add':
        data = load_data()
        cfg = _get_cfg(data)
        parsed = _parse_blacklist_nicks(text)
        page = int(st.get('page') or 0)
        if len(parsed) != 1:
            _safe_edit(bot, chat_id, panel_msg_id, '❌ Отправьте ровно один ник без списка через запятую.', _cancel_kb(CB_BL_NICKS))
            return
        nick = parsed[0]
        existing = list(cfg.get('blacklist_nicks') or [])
        normalized = {_normalize_nick(str(item)) for item in existing}
        if _normalize_nick(nick) in normalized:
            _safe_edit(bot, chat_id, panel_msg_id, f'⚠️ Ник <code>{escape(nick)}</code> уже находится в чёрном списке.', _cancel_kb(CB_BL_NICKS))
            return
        existing.append(nick)
        cfg['blacklist_nicks'] = existing
        cfg['blacklist_enabled'] = True
        data['global'] = cfg
        save_data(data)
        _fsm.pop(chat_id, None)
        _log_event(str(chat_id), 'BLACKLIST', f'Ник добавлен в ЧС: {nick}', nick=nick)
        page, _ = _clamp_blacklist_nick_page(len(existing), page)
        if panel_msg_id:
            _safe_edit(bot, chat_id, panel_msg_id, _blacklist_nicks_text(chat_id, page, f'✅ Ник <code>{escape(nick)}</code> добавлен.'), _blacklist_nicks_kb(chat_id, page))
        return
    if mode == 'blacklist_text':
        data = load_data()
        cfg = _get_cfg(data)
        if text.strip() == '-':
            cfg['blacklist_text'] = _default_cfg()['blacklist_text']
            result_text = '✅ Текст ответа ЧС сброшен на стандартный.'
        else:
            cfg['blacklist_text'] = text.strip()
            result_text = '✅ Текст ответа ЧС обновлён.'
        data['global'] = cfg
        save_data(data)
        _fsm.pop(chat_id, None)
        if panel_msg_id:
            _safe_edit(bot, chat_id, panel_msg_id, result_text, _blacklist_kb())
        return
    if mode != 'add':
        return
    tmp = st.setdefault('tmp', {})
    if not panel_msg_id:
        return
    data = load_data()
    accounts = _get_accounts_for(chat_id, data)
    if step == 'secret':
        shared_secret = text
        if not generate_steam_guard_code(shared_secret):
            _safe_edit(bot, chat_id, panel_msg_id, '❌ <b>Невалидный shared_secret</b>.\n\nОтправь корректный shared_secret текстом или файл <b>.maFile</b>.', _cancel_kb(CB_SETTINGS))
            return
        tmp['shared_secret'] = shared_secret
        tmp['source'] = 'manual'
        st['step'] = 'name'
        _safe_edit(bot, chat_id, panel_msg_id, '🏷 <b>Ник аккаунта</b>\n\nВведи ник или название аккаунта. По нему бот предложит команду формата:\n<code>!code_ник</code>\n\nПример готовой команды: <code>!code_tinechelovec</code>', _cancel_kb(CB_SETTINGS))
        return
    if step == 'name':
        tmp['name'] = text
        tmp['command_nick'] = text
        _show_add_command_choice(bot, chat_id, panel_msg_id, st, accounts)
        return
    if step == 'command_choice':
        _safe_edit(bot, chat_id, panel_msg_id, 'Нажми кнопку: использовать предложенную команду или создать свою.', _add_command_choice_kb(str(tmp.get('suggested_command') or '!code_account')))
        return
    if step == 'command':
        cmd = _normalize_cmd(text)
        if not cmd:
            _safe_edit(bot, chat_id, panel_msg_id, '❌ Команда пустая. Введи ещё раз.', _cancel_kb(CB_SETTINGS))
            return
        reserved = {'sda_menu', '/sda_menu'}
        if cmd in reserved or cmd.lstrip('/') in reserved:
            _safe_edit(bot, chat_id, panel_msg_id, '❌ Команда зарезервирована. Введи другую.', _cancel_kb(CB_SETTINGS))
            return
        if any((_normalize_cmd(str(a.get('command', ''))) == cmd for a in accounts)):
            _safe_edit(bot, chat_id, panel_msg_id, '❌ Такая команда уже существует. Введи другую.', _cancel_kb(CB_SETTINGS))
            return
        tmp['command'] = cmd
        _show_add_limit_step(bot, chat_id, panel_msg_id, st)
        return
    if step == 'template_choice':
        _safe_edit(bot, chat_id, panel_msg_id, 'Выбери кнопкой, какой текст использовать: общий или кастомный.', _add_template_choice_kb())
        return
    if step == 'queue_choice':
        _safe_edit(bot, chat_id, panel_msg_id, 'Выбери кнопкой, использовать очередь для этого аккаунта или нет.', _add_queue_choice_kb())
        return
    if step == 'template_custom':
        custom_template = text.strip()
        if not custom_template:
            _safe_edit(bot, chat_id, panel_msg_id, '❌ Кастомный текст не может быть пустым. Напиши текст ещё раз.', _cancel_kb(CB_SETTINGS))
            return
        tmp['template'] = custom_template
        _show_add_queue_choice(bot, chat_id, panel_msg_id, st)
        return
    if step == 'limit':
        if 'name' not in tmp or 'command' not in tmp or 'shared_secret' not in tmp:
            _restart_add(bot, chat_id, panel_msg_id)
            return
        raw = text.strip()
        if raw == '-':
            tmp['limit'] = None
            tmp['period_hours'] = None
            _show_add_template_choice(bot, chat_id, panel_msg_id, st)
            return
        try:
            limit = int(raw)
            if limit <= 0:
                raise ValueError
        except ValueError:
            _safe_edit(bot, chat_id, panel_msg_id, '❌ Введи число > 0 или <code>-</code>.', _cancel_kb(CB_SETTINGS))
            return
        tmp['limit'] = limit
        st['step'] = 'period'
        _safe_edit(bot, chat_id, panel_msg_id, '⏱ <b>Период лимита</b>\n\nЕсли период = 24 — лимит обновится через 24 часа.\nЕсли период = <code>0</code> или <code>-</code> — лимит будет навсегда для каждого покупателя.\n\nПримеры: <code>24</code> / <code>0</code> / <code>-</code>', _cancel_kb(CB_SETTINGS))
        return
    if step == 'period':
        if 'name' not in tmp or 'command' not in tmp or 'shared_secret' not in tmp or ('limit' not in tmp):
            _restart_add(bot, chat_id, panel_msg_id)
            return
        raw = text.strip()
        if raw in {'-', '0'}:
            tmp['period_hours'] = None
            _show_add_template_choice(bot, chat_id, panel_msg_id, st)
            return
        try:
            hours = int(raw)
            if hours <= 0:
                raise ValueError
        except ValueError:
            _safe_edit(bot, chat_id, panel_msg_id, '❌ Введи число > 0, либо <code>-</code> / <code>0</code>.', _cancel_kb(CB_SETTINGS))
            return
        tmp['period_hours'] = hours
        _show_add_template_choice(bot, chat_id, panel_msg_id, st)
        return
    _restart_add(bot, chat_id, panel_msg_id)

def _delete_plugin_text() -> str:
    return (f'⚠️ <b>Удаление плагина</b>\n\nВы точно хотите удалить <b>{escape(NAME)}</b>?\n\n'
            'Будут удалены:\n• основной файл плагина\n• аккаунты и настройки\n• очередь, статистика и логи\n\n'
            '<b>Действие необратимо.</b> После удаления выполните <code>/restart</code>.')

def _delete_plugin_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton('✅ Да, удалить', callback_data=CB_DELETE_PLUGIN_YES), InlineKeyboardButton('❌ Нет', callback_data=CB_DELETE_PLUGIN_NO))
    return kb

def _delete_plugin_open(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call)
    _safe_edit(bot, call.message.chat.id, _mid(call.message), _delete_plugin_text(), _delete_plugin_kb())

def _delete_plugin_no(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    _answer_cbq(bot, call, 'Отменено.')
    open_welcome(cardinal, call)

def _delete_plugin_files() -> tuple[bool, List[str]]:
    errors = []
    _cancel_all_queue_timers()
    try:
        shutil.rmtree(PLUGIN_FOLDER, ignore_errors=False)
    except FileNotFoundError:
        pass
    except Exception as error:
        errors.append(f'Не удалось удалить данные: {error}')
    plugin_file = os.path.abspath(__file__)
    try:
        _cleanup_plugin_bytecode(plugin_file)
        os.remove(plugin_file)
    except FileNotFoundError:
        pass
    except Exception as error:
        errors.append(f'Не удалось удалить файл плагина: {error}')
    for suffix in ('.update.pending', '.update.tmp', '.local-update.tmp'):
        try:
            path = plugin_file + suffix
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
    return not errors, errors

def _delete_plugin_try(cardinal: 'Cardinal', call):
    bot = cardinal.telegram.bot
    chat_id = call.message.chat.id
    _answer_cbq(bot, call, 'Удаляю…')
    ok, errors = _delete_plugin_files()
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton('🔙 К списку плагинов', callback_data=CBT_PLUGINS_LIST_OPEN))
    if ok:
        text = '✅ <b>Плагин удалён.</b>\n\n🔁 Чтобы применить удаление, выполните <code>/restart</code>.'
    else:
        text = '⚠️ <b>Удаление выполнено частично.</b>\n\n' + '\n'.join(f'• {escape(str(error))}' for error in errors[:10]) + '\n\nПосле ручного исправления выполните <code>/restart</code>.'
    try:
        bot.edit_message_text(text, chat_id, _mid(call.message), parse_mode='HTML', reply_markup=kb, disable_web_page_preview=True)
    except Exception:
        try:
            bot.send_message(chat_id, text, parse_mode='HTML', reply_markup=kb)
        except Exception:
            pass

def _debug_preview(text: str, limit: int=360) -> str:
    text = _mask_sensitive_debug_text(str(text or ''))
    text = text.replace('\r', '\\r').replace('\n', '\\n')
    if len(text) > limit:
        return text[:limit] + '…'
    return text

def _mask_sensitive_debug_text(text: str) -> str:
    text = str(text or '')
    text = re.sub('(Ваш\\s+код\\s*[:：]\\s*)[A-Z0-9]{5}', '\\1*****', text, flags=re.I)
    text = re.sub('(код\\s*[:：]\\s*)[A-Z0-9]{5}', '\\1*****', text, flags=re.I)
    return text

def _notify_debug(action: str, **fields):
    try:
        data = load_data()
        cfg = _get_cfg(data)
        if not bool(cfg.get('command_notifications_debug_enabled', True)):
            return
    except Exception:
        pass
    try:
        safe_fields = {}
        for k, v in (fields or {}).items():
            if isinstance(v, str):
                safe_fields[k] = _mask_sensitive_debug_text(v)
            else:
                safe_fields[k] = v
        rec = {'ts': int(time.time()), 'dt': datetime.fromtimestamp(int(time.time())).strftime('%d.%m.%Y %H:%M:%S'), 'action': str(action), **safe_fields}
        line = json.dumps(rec, ensure_ascii=False, default=str)
        with _notify_debug_lock:
            os.makedirs(PLUGIN_FOLDER, exist_ok=True)
            with open(NOTIFY_DEBUG_FILE, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
            try:
                if os.path.getsize(NOTIFY_DEBUG_FILE) > 700000:
                    with open(NOTIFY_DEBUG_FILE, 'r', encoding='utf-8') as f:
                        lines = f.readlines()[-900:]
                    with open(NOTIFY_DEBUG_FILE, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
            except Exception:
                pass
        summary = ', '.join((f'{k}={_debug_preview(str(v), 140)}' for k, v in list(safe_fields.items())[:6]))
        logger.info(f'{PREFIX} [notify-debug] {action}' + (f': {summary}' if summary else ''))
    except Exception:
        pass

def _looks_like_new_message_notification_text(text: str) -> bool:
    plain = _html_to_plain(str(text or '')).casefold()
    return any((x in plain for x in ('новое сообщение', 'новые сообщения', 'new message', 'new messages', 'переписк', 'cid:', '┌──', '└──')))

def _looks_like_command_notification_text(text: str) -> bool:
    plain = _html_to_plain(str(text or '')).casefold()
    return 'команд' in plain or 'command' in plain

def _candidate_message_texts_from_notification(text: str) -> List[str]:
    plain = _html_to_plain(str(text or ''))
    candidates = []
    for code in _block_code_values(text):
        if str(code or '').strip():
            candidates.append(str(code).strip())
    for raw_line in plain.splitlines():
        line = str(raw_line or '').strip()
        if not line:
            continue
        cleaned = re.sub('^[\\s│┃┌└┘├┬┴─>\\-—→]+', '', line).strip()
        if cleaned:
            candidates.append(cleaned)
        if ':' in cleaned:
            tail = cleaned.split(':', 1)[1].strip()
            if tail:
                candidates.append(tail)
        if '：' in cleaned:
            tail = cleaned.split('：', 1)[1].strip()
            if tail:
                candidates.append(tail)
    result = []
    seen = set()
    for item in candidates:
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result

def _notification_text_has_exact_command_line(text: str, data: Optional[dict]=None) -> bool:
    if data is None:
        data = load_data()
    for candidate in _candidate_message_texts_from_notification(text):
        candidate = re.sub('^[>\\-—→\\s]+', '', str(candidate or '')).strip()
        if _is_exact_plugin_command(candidate, data):
            return True
    return False

def _should_suppress_any_notification_text(text: str, data: Optional[dict]=None, source: str='') -> bool:
    if data is None:
        data = load_data()
    cfg = _get_cfg(data)
    if not bool(cfg.get('plugin_enabled', True)):
        return False
    text = str(text or '')
    if not text.strip():
        return False
    looks_relevant = _looks_like_new_message_notification_text(text) or _looks_like_command_notification_text(text) or _notification_text_has_exact_command_line(text, data)
    if not looks_relevant:
        return False
    if _notification_text_has_exact_command_line(text, data):
        _notify_debug('suppress_by_exact_command_line', source=source, preview=_debug_preview(text), candidates=_candidate_message_texts_from_notification(text)[:12])
        return True
    if _has_recent_command_notification_suppression() and _looks_like_new_message_notification_text(text):
        _notify_debug('suppress_by_recent_command_window', source=source, preview=_debug_preview(text))
        return True
    return False

def _patch_telegram_bot_send_message(cardinal: 'Cardinal') -> bool:
    tg = getattr(cardinal, 'telegram', None)
    bot = getattr(tg, 'bot', None) if tg is not None else None
    if bot is None:
        _notify_debug('patch_bot_send_message_missing', reason='cardinal.telegram.bot is None')
        return False
    original = getattr(bot, 'send_message', None)
    if not callable(original):
        _notify_debug('patch_bot_send_message_missing', reason='bot.send_message is not callable', bot_type=str(type(bot)))
        return False
    if _callable_chain_has_attr(original, '_steam_guard_sda_wrapped'):
        return True

    def wrapped_bot_send_message(chat_id, text, *args, _original=original, **kwargs):
        try:
            data = load_data()
            if _should_suppress_any_notification_text(str(text or ''), data, source='telegram.bot.send_message'):
                _notify_debug('bot_send_message_suppressed', chat_id=str(chat_id), preview=_debug_preview(str(text or '')))
                return None
        except Exception:
            pass
        return _original(chat_id, text, *args, **kwargs)
    wrapped_bot_send_message.__name__ = getattr(original, '__name__', 'send_message')
    wrapped_bot_send_message.__doc__ = getattr(original, '__doc__', None)
    wrapped_bot_send_message._steam_guard_sda_wrapped = True
    wrapped_bot_send_message._steam_guard_sda_original = original
    try:
        setattr(bot, 'send_message', wrapped_bot_send_message)
        _notify_debug('patch_bot_send_message_ok', bot_type=str(type(bot)))
        return True
    except Exception as e:
        _notify_debug('patch_bot_send_message_failed', error=str(e), bot_type=str(type(bot)))
        return False

def _patch_console_logger_filter() -> bool:
    global _original_logger_log
    with _logger_filter_lock:
        original = logging.Logger._log
        if _callable_chain_has_attr(original, '_steam_guard_sda_wrapped'):
            return True

        def wrapped_logger_log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
            try:
                rendered = str(msg)
                if args:
                    try:
                        rendered = rendered % args
                    except Exception:
                        rendered = str(msg)
                if _should_suppress_any_notification_text(rendered, None, source=f"logging.{getattr(self, 'name', '')}"):
                    _notify_debug('console_log_suppressed', logger_name=str(getattr(self, 'name', '')), level=int(level), preview=_debug_preview(rendered))
                    return None
            except Exception:
                pass
            return original(self, level, msg, args, exc_info=exc_info, extra=extra, stack_info=stack_info, stacklevel=stacklevel)
        wrapped_logger_log._steam_guard_sda_wrapped = True
        wrapped_logger_log._steam_guard_sda_original = original
        logging.Logger._log = wrapped_logger_log
        _original_logger_log = original
        _notify_debug('patch_console_logger_ok')
        return True

def _mark_recent_command_notification_suppression(seconds: int=15, chat_id=None, buyer_id: str='', cmd: str='', raw_text: str=''):
    global _suppress_own_notification_until
    try:
        until = time.time() + max(1, int(seconds))
        with _suppress_own_notification_lock:
            _suppress_own_notification_until = max(float(_suppress_own_notification_until or 0), until)
            _recent_command_suppressions.append({'until': until, 'chat_id': str(chat_id or ''), 'buyer_id': str(buyer_id or ''), 'cmd': _normalize_cmd(str(cmd or '')), 'raw_text': str(raw_text or '')})
            now = time.time()
            del _recent_command_suppressions[:-40]
            _recent_command_suppressions[:] = [x for x in _recent_command_suppressions if float(x.get('until') or 0) >= now]
        _notify_debug('recent_suppression_marked', seconds=int(seconds), chat_id=str(chat_id or ''), buyer_id=str(buyer_id or ''), cmd=_normalize_cmd(str(cmd or '')), raw_text=str(raw_text or ''))
    except Exception as e:
        _notify_debug('recent_suppression_mark_error', error=str(e))

def _has_recent_command_notification_suppression() -> bool:
    try:
        with _suppress_own_notification_lock:
            return time.time() <= float(_suppress_own_notification_until or 0)
    except Exception:
        return False

def _get_text_for_notification_check(event_msg) -> str:
    raw = _get_text_from_event_message(event_msg)
    if raw:
        return raw
    try:
        raw = str(event_msg)
    except Exception:
        raw = ''
    return (raw or '').strip()

def _stack_events_count(event) -> int:
    try:
        stack = getattr(event, 'stack', None)
        get_stack = getattr(stack, 'get_stack', None)
        if callable(get_stack):
            arr = get_stack() or []
            return len(arr)
    except Exception:
        pass
    return 1

def _iter_stack_event_messages(event):
    try:
        stack = getattr(event, 'stack', None)
        get_stack = getattr(stack, 'get_stack', None)
        if callable(get_stack):
            for item in get_stack() or []:
                msg = getattr(item, 'message', None)
                if msg is not None:
                    yield msg
            return
    except Exception:
        pass
    msg = getattr(event, 'message', None)
    if msg is not None:
        yield msg

def _is_own_or_bot_message(msg, cardinal: Optional['Cardinal']=None) -> bool:
    try:
        if bool(getattr(msg, 'by_bot', False)):
            return True
    except Exception:
        pass
    try:
        if cardinal is not None and int(getattr(msg, 'author_id', -1)) == int(getattr(cardinal.account, 'id', -2)):
            return True
    except Exception:
        pass
    return False

def _is_exact_plugin_command(raw_text: str, data: Optional[dict]=None) -> bool:
    text = _normalize_cmd(raw_text)
    if not text:
        return False
    if data is None:
        data = load_data()
    cfg = _get_cfg(data)
    if not bool(cfg.get('plugin_enabled', True)):
        return False
    matched = []
    for owner_uid, accounts in (data or {}).items():
        if owner_uid == 'global' or not isinstance(accounts, list):
            continue
        for acc in accounts:
            if not isinstance(acc, dict):
                continue
            cmd = _normalize_cmd(str(acc.get('command', '') or ''))
            if cmd and text == cmd:
                matched.append(acc)
    if not matched:
        return False
    return all((not _account_command_notifications_effective(acc, cfg) for acc in matched))

def _get_plugin_commands(data: Optional[dict]=None) -> set:
    if data is None:
        data = load_data()
    commands = set()
    for owner_uid, accounts in (data or {}).items():
        if owner_uid == 'global' or not isinstance(accounts, list):
            continue
        for acc in accounts:
            if not isinstance(acc, dict):
                continue
            cmd = _normalize_cmd(str(acc.get('command', '') or ''))
            if cmd:
                commands.add(cmd)
    return commands

def _should_skip_command_message_notification(event: NewMessageEvent, cardinal: Optional['Cardinal']=None) -> bool:
    data = load_data()
    cfg = _get_cfg(data)
    if not bool(cfg.get('plugin_enabled', True)):
        return False
    buyer_messages = []
    for msg in _iter_stack_event_messages(event):
        if _is_own_or_bot_message(msg, cardinal):
            continue
        raw_text = _get_text_for_notification_check(msg)
        if raw_text:
            buyer_messages.append(raw_text)
    if not buyer_messages:
        raw_text = _get_text_for_notification_check(getattr(event, 'message', None))
        buyer_messages = [raw_text] if raw_text else []
    should_skip = bool(buyer_messages) and all((_is_exact_plugin_command(x, data) for x in buyer_messages))
    _notify_debug('handler_notification_check', buyer_messages=buyer_messages, should_skip=bool(should_skip), stack_count=_stack_events_count(event))
    if should_skip:
        _mark_recent_command_notification_suppression(raw_text=' | '.join(buyer_messages))
    return should_skip

def _html_to_plain(s: str) -> str:
    s = re.sub('<br\\s*/?>', '\n', str(s or ''), flags=re.I)
    s = re.sub('<[^>]+>', '', s)
    return unescape(s).strip()

def _notification_type_to_text(notification_type) -> str:
    parts = []
    for attr in ('name', 'value'):
        try:
            value = getattr(notification_type, attr, None)
            if value is not None:
                parts.append(str(value))
        except Exception:
            pass
    try:
        parts.append(str(notification_type))
    except Exception:
        pass
    return ' '.join(parts).casefold()

def _notification_type_from_call(args: tuple, kwargs: dict):
    if len(args) >= 3:
        return args[2]
    return kwargs.get('notification_type')

def _is_new_message_notification_type(notification_type) -> bool:
    s = _notification_type_to_text(notification_type)
    return 'new_message' in s or 'new message' in s or 'newmessage' in s

def _is_command_notification_type(notification_type) -> bool:
    s = _notification_type_to_text(notification_type)
    return 'command' in s or 'команд' in s

def _split_notification_blocks(text: str) -> List[str]:
    text = str(text or '')
    blocks = [b for b in re.split('(?:\\r?\\n){2,}', text) if b.strip()]
    return blocks or ([text] if text.strip() else [])

def _block_code_values(block: str) -> List[str]:
    values = []
    for raw in re.findall('<code>(.*?)</code>', str(block or ''), flags=re.I | re.S):
        values.append(_html_to_plain(raw))
    return values

def _block_author_plain(block: str) -> str:
    part = re.split('<code>|<a\\s', str(block or ''), maxsplit=1, flags=re.I)[0]
    return _html_to_plain(part).casefold()

def _block_is_own_or_bot(block: str) -> bool:
    author = _block_author_plain(block)
    return 'вы' in author or 'бот' in author

def _block_is_exact_command(block: str, data: Optional[dict]=None) -> bool:
    codes = _block_code_values(block)
    if not codes:
        plain = _html_to_plain(block)
        return _is_exact_plugin_command(plain, data)
    return any((_is_exact_plugin_command(code, data) for code in codes))

def _should_suppress_new_message_text(text: str, data: Optional[dict]=None) -> bool:
    if data is None:
        data = load_data()
    blocks = _split_notification_blocks(text)
    user_blocks = [b for b in blocks if not _block_is_own_or_bot(b)]
    if not user_blocks:
        return _has_recent_command_notification_suppression()
    user_has_exact_command = any((_block_is_exact_command(b, data) for b in user_blocks))
    user_has_other_text = any((not _block_is_exact_command(b, data) for b in user_blocks))
    return user_has_exact_command and (not user_has_other_text)

def _strip_exact_command_blocks_from_notification_text(text: str, data: Optional[dict]=None) -> str:
    if data is None:
        data = load_data()
    blocks = _split_notification_blocks(text)
    kept = []
    for block in blocks:
        if not _block_is_own_or_bot(block) and _block_is_exact_command(block, data):
            continue
        kept.append(block)
    return '\n\n'.join(kept).strip()

def _should_suppress_command_notification_text(text: str, data: Optional[dict]=None) -> bool:
    if data is None:
        data = load_data()
    return _notification_text_has_exact_command_line(text, data)

def _filter_notification_call(args: tuple, kwargs: dict) -> tuple[bool, tuple, dict]:
    data = load_data()
    cfg = _get_cfg(data)
    if not bool(cfg.get('plugin_enabled', True)):
        return (True, args, kwargs)
    if not args:
        _notify_debug('send_notification_seen_without_args', kwargs=list((kwargs or {}).keys()))
        return (True, args, kwargs)
    notification_type = _notification_type_from_call(args, kwargs)
    text = str(args[0] or '')
    _notify_debug('send_notification_seen', notification_type=_notification_type_to_text(notification_type), args_len=len(args), kwargs_keys=list((kwargs or {}).keys()), preview=_debug_preview(text))
    if _should_suppress_any_notification_text(text, data, source='telegram.send_notification'):
        return (False, args, kwargs)
    if _is_new_message_notification_type(notification_type):
        if _should_suppress_new_message_text(text, data):
            _notify_debug('send_notification_suppressed_new_message', preview=_debug_preview(text))
            return (False, args, kwargs)
        filtered = _strip_exact_command_blocks_from_notification_text(text, data)
        if not filtered:
            _notify_debug('send_notification_suppressed_empty_after_filter', preview=_debug_preview(text))
            return (False, args, kwargs)
        if filtered != text:
            _notify_debug('send_notification_filtered_text', before=_debug_preview(text), after=_debug_preview(filtered))
            args = (filtered,) + tuple(args[1:])
        return (True, args, kwargs)
    if _is_command_notification_type(notification_type):
        if _should_suppress_command_notification_text(text, data):
            _notify_debug('send_notification_suppressed_command_type', preview=_debug_preview(text))
            return (False, args, kwargs)
    return (True, args, kwargs)

def _patch_telegram_send_notification(cardinal: 'Cardinal') -> bool:
    tg = getattr(cardinal, 'telegram', None)
    if tg is None:
        _notify_debug('patch_send_notification_missing', reason='cardinal.telegram is None')
        return False
    original = getattr(tg, 'send_notification', None)
    if not callable(original):
        _notify_debug('patch_send_notification_missing', reason='telegram.send_notification is not callable', telegram_type=str(type(tg)))
        return False
    if getattr(original, '_steam_guard_sda_wrapped', False):
        return True

    def wrapped_send_notification(*args, _original=original, **kwargs):
        try:
            allowed, new_args, new_kwargs = _filter_notification_call(tuple(args), dict(kwargs))
            if not allowed:
                return None
            return _original(*new_args, **new_kwargs)
        except Exception as e:
            logger.error(f'{PREFIX} notification send filter error: {e}')
            return _original(*args, **kwargs)
    wrapped_send_notification.__name__ = getattr(original, '__name__', 'send_notification')
    wrapped_send_notification.__doc__ = getattr(original, '__doc__', None)
    wrapped_send_notification._steam_guard_sda_wrapped = True
    wrapped_send_notification._steam_guard_sda_original = original
    try:
        setattr(tg, 'send_notification', wrapped_send_notification)
        logger.info(f'{PREFIX} Фильтр TG-уведомлений команд установлен.')
        _notify_debug('patch_send_notification_ok', telegram_type=str(type(tg)))
        return True
    except Exception as e:
        logger.error(f'{PREFIX} Не смог установить фильтр TG-уведомлений: {e}')
        _notify_debug('patch_send_notification_failed', error=str(e), telegram_type=str(type(tg)))
        return False

def _patch_new_message_notifications(cardinal: 'Cardinal'):
    _patch_telegram_send_notification(cardinal)
    if getattr(cardinal, '_steam_guard_sda_notification_patch', False):
        return
    possible_lists = []
    for attr in ('new_message_handlers', 'BIND_TO_NEW_MESSAGE'):
        handlers = getattr(cardinal, attr, None)
        if isinstance(handlers, list):
            possible_lists.append(handlers)
    try:
        import handlers as fpc_handlers
        handlers = getattr(fpc_handlers, 'BIND_TO_NEW_MESSAGE', None)
        if isinstance(handlers, list):
            possible_lists.append(handlers)
    except Exception:
        pass
    try:
        handler_names = []
        for handlers in possible_lists:
            handler_names.append([getattr(h, '__name__', str(h)) for h in list(handlers)[:40]])
        _notify_debug('handler_lists_found', lists_count=len(possible_lists), names=handler_names, cardinal_type=str(type(cardinal)))
    except Exception:
        pass
    target_names = {'log_msg_handler', 'send_new_message_notification_handler', 'send_command_notification_handler'}
    patched_any = False
    for handlers in possible_lists:
        for idx, handler in enumerate(list(handlers)):
            name = getattr(handler, '__name__', '')
            if name not in target_names or getattr(handler, '_steam_guard_sda_wrapped', False):
                continue
            original_handler = handler

            def wrapped_notification_handler(cardinal_arg, event_arg, *h_args, _original=original_handler, **h_kwargs):
                try:
                    if _should_skip_command_message_notification(event_arg, cardinal_arg):
                        return
                except Exception:
                    pass
                return _original(cardinal_arg, event_arg, *h_args, **h_kwargs)
            wrapped_notification_handler.__name__ = getattr(original_handler, '__name__', 'notification_handler')
            wrapped_notification_handler.__doc__ = getattr(original_handler, '__doc__', None)
            wrapped_notification_handler.plugin_uuid = getattr(original_handler, 'plugin_uuid', None)
            wrapped_notification_handler._steam_guard_sda_wrapped = True
            wrapped_notification_handler._steam_guard_sda_original = original_handler
            handlers[idx] = wrapped_notification_handler
            patched_any = True
    setattr(cardinal, '_steam_guard_sda_notification_patch', True)
    if patched_any:
        logger.info(f'{PREFIX} SAFE-фильтр handlers уведомлений команд установлен.')
    _notify_debug('handler_patch_result_safe', patched_any=bool(patched_any))

def _get_text_from_event_message(event_msg) -> str:
    return (getattr(event_msg, 'text', '') or '').strip()

def _get_buyer_id_from_event_message(event_msg) -> str:
    for attr in ('user_id', 'from_id', 'sender_id'):
        val = getattr(event_msg, attr, None)
        if val:
            return str(val if isinstance(val, (int, str)) else getattr(val, 'id', ''))
    return str(getattr(event_msg, 'chat_id', ''))

def _format_time_left(seconds: int) -> str:
    m, s = divmod(max(0, int(seconds)), 60)
    h, m = divmod(m, 60)
    if h:
        return f'{h}ч {m}м'
    if m:
        return f'{m}м'
    return f'{s}с'

def _current_window() -> int:
    return int(time.time()) // 30

def _seconds_to_next_slot(now: Optional[int]=None) -> int:
    if now is None:
        now = int(time.time())
    return 30 - now % 30

def _account_key(owner_uid: str, acc: dict) -> str:
    return f"{owner_uid}::{_normalize_cmd(str(acc.get('command', '') or ''))}::{str(acc.get('name', '') or '')}"

def _cleanup_queue_state(q: dict):
    now = int(time.time())
    for key, state in list(q.items()):
        if not isinstance(state, dict):
            q.pop(key, None)
            continue
        queue_arr = state.get('queue')
        if not isinstance(queue_arr, list):
            state['queue'] = []
            queue_arr = state['queue']
        fresh = []
        for item in queue_arr:
            try:
                enq = int(item.get('enqueued_at') or now)
                if now - enq <= 86400:
                    fresh.append(item)
            except Exception:
                continue
        state['queue'] = fresh
        last_window = int(state.get('last_window') or -1)
        active_until = int(state.get('active_until') or 0)
        if active_until and now >= active_until:
            state['active_buyer'] = None
            state['active_chat_id'] = None
            state['active_until'] = 0
        if not state.get('queue') and (not state.get('active_buyer')) and (last_window < _current_window() - 3):
            q.pop(key, None)

def _ensure_queue_state(q: dict, account_key: str) -> dict:
    st = q.get(account_key)
    if not isinstance(st, dict):
        st = {'last_window': -1, 'active_buyer': None, 'active_chat_id': None, 'active_until': 0, 'queue': []}
        q[account_key] = st
    if not isinstance(st.get('queue'), list):
        st['queue'] = []
    return st

def _find_queue_item(queue_arr: List[dict], buyer_id: str) -> Optional[int]:
    for i, item in enumerate(queue_arr):
        if str(item.get('buyer_id')) == str(buyer_id):
            return i
    return None

def _make_queue_item(owner_uid: str, acc: dict, buyer_id: str, chat_id, cmd: str, now: Optional[int]=None) -> dict:
    if now is None:
        now = int(time.time())
    return {'buyer_id': str(buyer_id), 'chat_id': chat_id, 'owner_uid': owner_uid, 'name': str(acc.get('name') or ''), 'command': cmd, 'shared_secret': str(acc.get('shared_secret') or ''), 'limit': acc.get('limit'), 'period_hours': acc.get('period_hours'), 'template': str(acc.get('template') or ''), 'enqueued_at': now}

def _queue_delay_from_state(st: dict, now: Optional[int]=None) -> int:
    if now is None:
        now = int(time.time())
    if st.get('active_buyer'):
        return max(1, int(st.get('active_until') or now) - now)
    return 1

def _get_usage_record(usage: dict, owner_uid: str, buyer_id: str, cmd: str) -> dict:
    usage.setdefault(owner_uid, {}).setdefault(buyer_id, {})
    usage[owner_uid][buyer_id].setdefault(cmd, {'count': 0})
    return usage[owner_uid][buyer_id][cmd]

def _check_limit_only(usage: dict, owner_uid: str, buyer_id: str, cmd: str, limit, period_hours, now: int):
    if limit is None:
        return (True, None, None)
    limit = int(limit)
    record = _get_usage_record(usage, owner_uid, buyer_id, cmd)
    if period_hours is None:
        if int(record.get('count') or 0) >= limit:
            return (False, f'❌ Лимит {limit} навсегда исчерпан.', 0)
        return (True, None, None)
    period_seconds = int(period_hours) * 3600
    record.setdefault('reset_time', now + period_seconds)
    if now > int(record['reset_time']):
        record['count'] = 0
        record['reset_time'] = now + period_seconds
    if int(record.get('count') or 0) >= limit:
        seconds_left = int(record['reset_time'] - now)
        return (False, f'❌ Лимит исчерпан. Новый запрос через {_format_time_left(seconds_left)}.', seconds_left)
    return (True, None, None)

def _commit_usage_increment(usage: dict, owner_uid: str, buyer_id: str, cmd: str, limit, period_hours, now: int):
    if limit is None:
        return ('∞', '∞')
    limit = int(limit)
    record = _get_usage_record(usage, owner_uid, buyer_id, cmd)
    if period_hours is not None:
        period_seconds = int(period_hours) * 3600
        record.setdefault('reset_time', now + period_seconds)
        if now > int(record['reset_time']):
            record['count'] = 0
            record['reset_time'] = now + period_seconds
    record['count'] = int(record.get('count') or 0) + 1
    left = max(0, limit - int(record['count']))
    total = '∞' if period_hours is None else str(limit)
    return (str(left), str(total))

def _cancel_timer(account_key: str):
    with _timer_lock:
        timer = _queue_timers.pop(account_key, None)
        if timer:
            try:
                timer.cancel()
            except Exception:
                pass

def _schedule_queue_processing(cardinal: 'Cardinal', account_key: str, delay: int):

    def _runner():
        current_timer = threading.current_thread()
        try:
            _process_queue_for_account(cardinal, account_key)
        finally:
            with _timer_lock:
                if _queue_timers.get(account_key) is current_timer:
                    _queue_timers.pop(account_key, None)
    with _timer_lock:
        old = _queue_timers.get(account_key)
        if old:
            try:
                old.cancel()
            except Exception:
                pass
        t = threading.Timer(max(1, int(delay)), _runner)
        t.daemon = True
        _queue_timers[account_key] = t
        t.start()

def _send_queue_position_message(cardinal: 'Cardinal', chat_id: int, pos: int, seconds_wait: int, total_people: int):
    if pos <= 1:
        text = f'⏳ Код сейчас занят. Ты следующий в очереди.\nПримерное ожидание: {seconds_wait}с.'
    else:
        text = f'⏳ Ты добавлен в очередь.\nПозиция: {pos}\nЛюдей в очереди: {total_people}\nПримерное ожидание: {seconds_wait}с.'
    cardinal.account.send_message(chat_id, text)

def _enqueue_buyer(cardinal: 'Cardinal', account_key: str, owner_uid: str, acc: dict, buyer_id: str, chat_id, cmd: str):
    now = int(time.time())
    with _queue_lock, _usage_lock:
        q = load_queue()
        usage = load_usage()
        _cleanup_queue_state(q)
        st = _ensure_queue_state(q, account_key)
        ok, err_msg, _ = _check_limit_only(usage, owner_uid, buyer_id, cmd, acc.get('limit'), acc.get('period_hours'), now)
        save_usage(usage)
        if not ok:
            save_queue(q)
            cardinal.account.send_message(chat_id, err_msg)
            _push_log(owner_uid, {'ts': now, 'type': 'LIMIT', 'name': str(acc.get('name') or ''), 'cmd': cmd, 'buyer': buyer_id, 'msg': 'лимит не позволил встать в очередь'})
            return True
        if str(st.get('active_buyer') or '') == str(buyer_id):
            idx = _find_queue_item(st['queue'], buyer_id)
            if idx is None:
                st['queue'].append(_make_queue_item(owner_uid, acc, buyer_id, chat_id, cmd, now))
                pos = len(st['queue'])
                msg_prefix = '⏳ Текущий слот уже закреплён за тобой. Добавил тебя в очередь на следующий код.'
                _log_event(str(owner_uid), 'QUEUE', 'Покупатель добавлен в очередь на следующий код', name=str(acc.get('name') or ''), cmd=cmd, buyer=buyer_id, position=pos)
            else:
                pos = idx + 1
                msg_prefix = '⏳ Ты уже есть в очереди на следующий код.'
                _log_event(str(owner_uid), 'QUEUE', 'Повторный запрос: покупатель уже в очереди', name=str(acc.get('name') or ''), cmd=cmd, buyer=buyer_id, position=pos)
            active_left = _queue_delay_from_state(st, now)
            eta = active_left + (pos - 1) * 30
            save_queue(q)
            cardinal.account.send_message(chat_id, f'{msg_prefix}\nПозиция: {pos}\nПримерное ожидание: {eta}с.')
            _schedule_queue_processing(cardinal, account_key, active_left)
            return True
        idx = _find_queue_item(st['queue'], buyer_id)
        if idx is not None:
            pos = idx + 1
            active_slot = 1 if st.get('active_buyer') else 0
            eta = _queue_delay_from_state(st, now) + (pos - 1) * 30
            delay = _queue_delay_from_state(st, now)
            save_queue(q)
            _log_event(str(owner_uid), 'QUEUE', 'Показана текущая позиция в очереди', name=str(acc.get('name') or ''), cmd=cmd, buyer=buyer_id, position=pos)
            _send_queue_position_message(cardinal, chat_id, pos, eta, len(st['queue']) + active_slot)
            _schedule_queue_processing(cardinal, account_key, delay)
            return True
        item = _make_queue_item(owner_uid, acc, buyer_id, chat_id, cmd, now)
        st['queue'].append(item)
        _log_event(str(owner_uid), 'QUEUE', 'Покупатель добавлен в очередь', name=str(acc.get('name') or ''), cmd=cmd, buyer=buyer_id, position=len(st['queue']))
        save_queue(q)
        pos = len(st['queue'])
        active_slot = 1 if st.get('active_buyer') else 0
        delay = _queue_delay_from_state(st, now)
        eta = delay + (pos - 1) * 30
        _send_queue_position_message(cardinal, chat_id, pos, eta, len(st['queue']) + active_slot)
    _schedule_queue_processing(cardinal, account_key, delay)
    return True

def _process_queue_for_account(cardinal: 'Cardinal', account_key: str):
    try:
        _, live_acc, live_cfg = _find_live_account_by_key(account_key)
        if live_acc is None or not _account_queue_effective(live_acc, live_cfg):
            return
        now = int(time.time())
        with _queue_lock, _usage_lock:
            q = load_queue()
            usage = load_usage()
            _cleanup_queue_state(q)
            st = q.get(account_key)
            if not isinstance(st, dict):
                save_queue(q)
                save_usage(usage)
                return
            queue_arr = st.get('queue') or []
            if not queue_arr:
                st['active_buyer'] = None
                st['active_chat_id'] = None
                st['active_until'] = 0
                save_queue(q)
                save_usage(usage)
                return
            current_window = _current_window()
            last_window = int(st.get('last_window') or -1)
            if last_window == current_window:
                delay = _seconds_to_next_slot(now)
                save_queue(q)
                save_usage(usage)
                _schedule_queue_processing(cardinal, account_key, delay)
                return
            item = queue_arr.pop(0)
            owner_uid = str(item.get('owner_uid') or '')
            buyer_id = str(item.get('buyer_id') or '')
            chat_id = item.get('chat_id')
            name = str(item.get('name') or '')
            cmd = str(item.get('command') or '')
            shared = str(item.get('shared_secret') or '')
            limit = item.get('limit')
            period_hours = item.get('period_hours')
            account_template = str(item.get('template') or '')
            ok, err_msg, wait_seconds = _check_limit_only(usage, owner_uid, buyer_id, cmd, limit, period_hours, now)
            if not ok:
                save_usage(usage)
                save_queue(q)
                try:
                    cardinal.account.send_message(chat_id, err_msg)
                except Exception:
                    pass
                _push_log(owner_uid, {'ts': now, 'type': 'LIMIT', 'name': name, 'cmd': cmd, 'buyer': buyer_id, 'msg': f'очередь снята лимитом ({wait_seconds or 0}s)'})
                if st.get('queue'):
                    delay = _seconds_to_next_slot(now)
                    _schedule_queue_processing(cardinal, account_key, delay)
                return
            code = generate_steam_guard_code(shared)
            if not code:
                save_usage(usage)
                save_queue(q)
                try:
                    cardinal.account.send_message(chat_id, '❌ Ошибка генерации.')
                except Exception:
                    pass
                _push_log(owner_uid, {'ts': now, 'type': 'ERROR', 'name': name, 'cmd': cmd, 'buyer': buyer_id, 'msg': 'ошибка генерации из очереди'})
                if st.get('queue'):
                    delay = _seconds_to_next_slot(now)
                    _schedule_queue_processing(cardinal, account_key, delay)
                return
            left, total = _commit_usage_increment(usage, owner_uid, buyer_id, cmd, limit, period_hours, now)
            st['last_window'] = current_window
            st['active_buyer'] = buyer_id
            st['active_chat_id'] = chat_id
            st['active_until'] = (current_window + 1) * 30
            save_usage(usage)
            save_queue(q)
        data = load_data()
        cfg = _get_cfg(data)
        tpl = _get_template_by_mode(account_template, cfg)
        msg = _render_template(tpl, {'code': code, 'name': name, 'command': cmd, 'left': str(left), 'total': str(total), 'limit_text': _limit_text({'limit': limit, 'period_hours': period_hours})})
        cardinal.account.send_message(chat_id, msg)
        _push_log(owner_uid, {'ts': now, 'type': 'CODE', 'name': name, 'cmd': cmd, 'buyer': buyer_id, 'msg': f'выдан из очереди, осталось {left}/{total}'})
        with _queue_lock:
            q = load_queue()
            st = q.get(account_key)
            _, live_acc, live_cfg = _find_live_account_by_key(account_key)
            if isinstance(st, dict) and st.get('queue') and (live_acc is not None) and _account_queue_effective(live_acc, live_cfg):
                delay = _seconds_to_next_slot()
                save_queue(q)
                _schedule_queue_processing(cardinal, account_key, delay)
            else:
                save_queue(q)
    except Exception as e:
        logger.exception(f'{PREFIX} _process_queue_for_account error: {e}')
        _log_error_for_all_owners('_process_queue_for_account', e)

def _issue_now(cardinal: 'Cardinal', owner_uid: str, acc: dict, buyer_id: str, chat_id, cmd: str):
    now = int(time.time())
    account_key = _account_key(owner_uid, acc)
    with _queue_lock, _usage_lock:
        q = load_queue()
        usage = load_usage()
        _cleanup_queue_state(q)
        st = _ensure_queue_state(q, account_key)
        ok, err_msg, wait_seconds = _check_limit_only(usage, owner_uid, buyer_id, cmd, acc.get('limit'), acc.get('period_hours'), now)
        if not ok:
            save_usage(usage)
            save_queue(q)
            cardinal.account.send_message(chat_id, err_msg)
            _push_log(owner_uid, {'ts': now, 'type': 'LIMIT', 'name': str(acc.get('name') or ''), 'cmd': cmd, 'buyer': buyer_id, 'msg': f'лимит исчерпан ({wait_seconds or 0}s)'})
            return True
        code = generate_steam_guard_code(str(acc.get('shared_secret') or ''))
        if not code:
            save_usage(usage)
            save_queue(q)
            cardinal.account.send_message(chat_id, '❌ Ошибка генерации.')
            _push_log(owner_uid, {'ts': now, 'type': 'ERROR', 'name': str(acc.get('name') or ''), 'cmd': cmd, 'buyer': buyer_id, 'msg': 'ошибка генерации'})
            return True
        left, total = _commit_usage_increment(usage, owner_uid, buyer_id, cmd, acc.get('limit'), acc.get('period_hours'), now)
        current_window = _current_window()
        st['last_window'] = current_window
        st['active_buyer'] = buyer_id
        st['active_chat_id'] = chat_id
        st['active_until'] = (current_window + 1) * 30
        save_usage(usage)
        save_queue(q)
    data = load_data()
    cfg = _get_cfg(data)
    tpl = _get_account_template(acc, cfg)
    msg = _render_template(tpl, {'code': code, 'name': str(acc.get('name') or ''), 'command': cmd, 'left': str(left), 'total': str(total), 'limit_text': _limit_text(acc)})
    cardinal.account.send_message(chat_id, msg)
    _push_log(owner_uid, {'ts': now, 'type': 'CODE', 'name': str(acc.get('name') or ''), 'cmd': cmd, 'buyer': buyer_id, 'msg': f'выдан, осталось {left}/{total}'})
    data = load_data()
    cfg = _get_cfg(data)
    if _account_queue_effective(acc, cfg):
        delay = _seconds_to_next_slot(now)
        _schedule_queue_processing(cardinal, account_key, delay)
    return True

def new_message_handler(cardinal: 'Cardinal', event: NewMessageEvent):
    try:
        _patch_new_message_notifications(cardinal)
        raw_text = _get_text_from_event_message(event.message)
        text = _normalize_cmd(raw_text)
        if not text:
            return
        buyer_id = _get_buyer_id_from_event_message(event.message)
        buyer_nick = _get_buyer_nick_from_event_message(event.message) or buyer_id
        chat_id = getattr(event.message, 'chat_id', None)
        if chat_id is None:
            return
        data = load_data()
        cfg = _get_cfg(data)
        if not bool(cfg.get('plugin_enabled', True)):
            return
        ids_changed = False
        for owner_uid, accounts in (data or {}).items():
            if owner_uid == 'global' or not isinstance(accounts, list):
                continue
            if _ensure_account_ids(str(owner_uid), accounts):
                ids_changed = True
        if ids_changed:
            save_data(data)
        for owner_uid, accounts in (data or {}).items():
            if owner_uid == 'global' or not isinstance(accounts, list):
                continue
            for acc in accounts:
                cmd_raw = str(acc.get('command', '') or '')
                cmd = _normalize_cmd(cmd_raw)
                if not cmd or text != cmd:
                    continue
                _log_event(str(owner_uid), 'COMMAND', 'Команда распознана', name=str(acc.get('name') or ''), cmd=cmd, buyer=str(buyer_id), nick=str(buyer_nick))
                account_enabled = bool(acc.get('enabled', True))
                account_queue_enabled = bool(cfg.get('queue_enabled', True)) and bool(acc.get('queue_enabled', True))
                if not _account_command_notifications_effective(acc, cfg):
                    _notify_debug('exact_sda_command_matched', chat_id=str(chat_id), buyer_id=str(buyer_id), buyer_nick=str(buyer_nick), cmd=str(cmd), raw_text=str(raw_text), account_name=str(acc.get('name') or ''))
                    _mark_recent_command_notification_suppression(chat_id=chat_id, buyer_id=buyer_id, cmd=cmd, raw_text=raw_text)
                if not account_enabled:
                    cardinal.account.send_message(chat_id, '❌ Выдача кодов для этого аккаунта временно отключена.')
                    _push_log(owner_uid, {'ts': int(time.time()), 'type': 'DISABLED', 'name': str(acc.get('name') or ''), 'cmd': cmd, 'buyer': buyer_id, 'nick': buyer_nick, 'msg': 'выдача кодов аккаунта выключена'})
                    return True
                if _try_blacklist_reject(cardinal, str(owner_uid), acc, buyer_id, buyer_nick, chat_id, cmd, cfg):
                    return True
                account_key = _account_key(owner_uid, acc)
                with _queue_lock:
                    q = load_queue()
                    _cleanup_queue_state(q)
                    st = _ensure_queue_state(q, account_key)
                    now = int(time.time())
                    current_window = _current_window()
                    active_until = int(st.get('active_until') or 0)
                    current_busy = st.get('active_buyer') and int(st.get('last_window') or -1) == current_window and (active_until > now)
                    busy_seconds = max(1, active_until - now)
                    save_queue(q)
                if current_busy:
                    if not account_queue_enabled:
                        cardinal.account.send_message(chat_id, f'❌ Код уже занят другим покупателем. Попробуйте через {_format_time_left(busy_seconds)}.')
                        _push_log(owner_uid, {'ts': int(time.time()), 'type': 'BUSY', 'name': str(acc.get('name') or ''), 'cmd': cmd, 'buyer': buyer_id, 'nick': buyer_nick, 'msg': f'очередь аккаунта или общая очередь выключена, ждать {busy_seconds}s'})
                        return
                    return _enqueue_buyer(cardinal, account_key, owner_uid, acc, buyer_id, chat_id, cmd)
                return _issue_now(cardinal, owner_uid, acc, buyer_id, chat_id, cmd)
    except Exception as e:
        logger.exception(f'{PREFIX} new_message_handler error: {e}')
        _log_error_for_all_owners('new_message_handler', e)

def _xor_unpack(values, seed):
    return ''.join(chr(value ^ ((seed + index * 29 + (index % 3) * 7) & 255)) for index, value in enumerate(values))

def _protected_author_meta():
    return {
        'CREDITS': _xor_unpack((27, 11, 202, 220, 179, 153, 97, 72, 61, 15, 242, 205, 212), 91),
        'UUID': _xor_unpack((207, 233, 205, 50, 26, 116, 99, 26, 142, 133, 239, 202, 49, 0, 101, 6, 178, 154, 154, 185, 155, 58, 10, 123, 81, 177, 200, 141, 129, 49, 112, 0, 58, 82, 235, 135), 173),
        'CREATOR_URL': _xor_unpack((81, 41, 245, 224, 199, 226, 200, 36, 91, 16, 15, 227, 186, 205, 180, 130, 117, 87, 43, 2, 231, 245, 200, 135, 146), 57),
    }

_AUTHOR_META_AT_LOAD = {'CREDITS': CREDITS, 'UUID': UUID, 'CREATOR_URL': CREATOR_URL}
_IMMUTABLE_META = _protected_author_meta()
_AUTHOR_META_KEYS = ('CREDITS', 'UUID', 'CREATOR_URL')
_IMMUTABLE_OK = True
_IMMUTABLE_REASON = ''
_AUTHOR_META_FIELDS = ('schema', 'plugin', 'credits', 'uuid', 'creatorUrl', 'issuedAt', 'expiresAt')
_AUTHOR_META_SHA256_PREFIX = bytes.fromhex('3031300d060960864801650304020105000420')
_AUTHOR_META_RSA_N = int(
        'c0014461db95102dfd52198bb728c80fe31064cdbc8dc4bda004e9603fea7e1c'
        '8f108a11dd44ce07feb44ccbc4077edba3185d305770105caeb7db57e4aafac3'
        '8917306fe9e439349f7349bb767d321dd902e7d829a780dc355daf6c139ead2d'
        '3d48eece29e1ee28bcccd99f7be5a0ac37d6682f1d3fe692531ad543f036fe7a'
        'ba837b436843edf4f565c05c2dab0a1950d5f671b411e254def8c9c08d2d7564'
        '750d1cb38283c4ae6ca1135dbf27266bbe4fd0b6d6dea72e4c7852bfe550b22c'
        '68a170b9fc2f3967617ef4cc5f374a66fc72e89565e7d91d0aa92cc16485514c'
        '0d63ba57bfb100646a828a897469ee4f77d88ca1f32d6d82489b369287a472e7'
    , 16)
_AUTHOR_META_RSA_E = 65537
_SERVER_META_LOCK = threading.RLock()
_SERVER_META_WATCH_STARTED = False
_SERVER_META_LAST_CHECK_TS = 0.0
_SERVER_META_LAST_OK_TS = 0.0
_TAMPER_RESTART_LOCK = threading.RLock()
_TAMPER_RESTART_WORKER_STARTED = False
_INTEGRITY_STATE_FILE = os.path.join(PLUGIN_FOLDER, 'integrity.json')
if not os.path.exists(_INTEGRITY_STATE_FILE):
    _save_json(_INTEGRITY_STATE_FILE, {'restart_count': 0, 'reason': '', 'updated_at': 0})

def _meta_guard():
    global _IMMUTABLE_OK, _IMMUTABLE_REASON
    if not _IMMUTABLE_OK:
        return False
    for key in _AUTHOR_META_KEYS:
        expected = _IMMUTABLE_META.get(key)
        loaded = _AUTHOR_META_AT_LOAD.get(key)
        current = globals().get(key)
        if loaded != expected:
            changed, scope = loaded, 'в исходном файле'
        elif current != expected:
            changed, scope = current, 'во время работы'
        else:
            continue
        _IMMUTABLE_OK = False
        if key == 'CREDITS':
            _IMMUTABLE_REASON = f'ник автора изменён на {changed or "неизвестный ник"} ({scope})'
        elif key == 'UUID':
            _IMMUTABLE_REASON = f'UUID плагина изменён ({scope})'
        else:
            _IMMUTABLE_REASON = f'ссылка автора изменена ({scope})'
        logger.critical(f'{PREFIX} [ANTI-TAMPER] {_IMMUTABLE_REASON}')
        _log_error_for_all_owners('anti_tamper_local', RuntimeError(_IMMUTABLE_REASON))
        return False
    return True

def _server_meta_message(payload):
    return '\n'.join(str(payload.get(key, '')) for key in _AUTHOR_META_FIELDS).encode('utf-8')

def _verify_server_meta_signature(payload, signature_text):
    try:
        signature = base64.b64decode(str(signature_text or ''), validate=True)
        key_size = (_AUTHOR_META_RSA_N.bit_length() + 7) // 8
        if len(signature) != key_size:
            return False
        encoded = pow(int.from_bytes(signature, 'big'), _AUTHOR_META_RSA_E, _AUTHOR_META_RSA_N).to_bytes(key_size, 'big')
        digest_info = _AUTHOR_META_SHA256_PREFIX + hashlib.sha256(_server_meta_message(payload)).digest()
        if not encoded.startswith(b'\x00\x01'):
            return False
        separator = encoded.find(b'\x00', 2)
        if separator < 10 or encoded[2:separator] != b'\xff' * (separator - 2):
            return False
        return encoded[separator + 1:] == digest_info
    except Exception:
        return False

def _fetch_signed_server_meta():
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen
    query = urlencode({'uuid': _IMMUTABLE_META['UUID']})
    url = 'https://fts-transfer-token.vercel.app/api/plugin-meta?' + query
    request = Request(url, headers={'Accept': 'application/json', 'User-Agent': f'{NAME}/{VERSION}'})
    with urlopen(request, timeout=15) as response:
        status = getattr(response, 'status', 200)
        envelope = json.loads(response.read().decode('utf-8'))
    if not isinstance(envelope, dict) or envelope.get('ok') is not True:
        raise ValueError('author API returned an invalid envelope')
    payload = envelope.get('payload')
    if not isinstance(payload, dict):
        raise ValueError('author API payload is missing')
    signature_ok = _verify_server_meta_signature(payload, envelope.get('signature'))
    if not signature_ok:
        return False, 'серверная подпись данных автора недействительна'
    now = int(time.time())
    try:
        issued_at, expires_at = int(payload.get('issuedAt')), int(payload.get('expiresAt'))
    except (TypeError, ValueError):
        return False, 'сервер вернул некорректный срок подписи'
    if issued_at > now + 120 or expires_at < now - 30:
        return False, 'серверная подпись данных автора устарела'
    if expires_at <= issued_at or expires_at - issued_at > 3600:
        return False, 'сервер вернул некорректный период подписи'
    expected = {'schema': 1, 'plugin': NAME, 'credits': CREDITS, 'uuid': UUID, 'creatorUrl': CREATOR_URL}
    labels = {'plugin': 'название плагина', 'credits': 'ник автора', 'uuid': 'UUID', 'creatorUrl': 'ссылка автора'}
    for key, current in expected.items():
        matched = payload.get(key) == current
        if not matched:
            return False, f'серверная проверка: не совпадает {labels.get(key, key)}'
    return True, ''

def _mark_server_meta_tamper(reason):
    global _IMMUTABLE_OK, _IMMUTABLE_REASON
    _IMMUTABLE_OK = False
    _IMMUTABLE_REASON = str(reason or 'серверная проверка данных автора не пройдена')
    logger.critical(f'{PREFIX} [ANTI-TAMPER] {_IMMUTABLE_REASON}')
    _log_error_for_all_owners('anti_tamper_server', RuntimeError(_IMMUTABLE_REASON))

def _run_server_meta_check(cardinal):
    global _SERVER_META_LAST_CHECK_TS, _SERVER_META_LAST_OK_TS
    with _SERVER_META_LOCK:
        _SERVER_META_LAST_CHECK_TS = time.time()
        try:
            ok, reason = _fetch_signed_server_meta()
        except Exception as e:
            return None
        if ok:
            _SERVER_META_LAST_OK_TS = time.time()
            return True
        _mark_server_meta_tamper(reason)
        _start_tamper_restart_cycle(cardinal, False)
        return False

def _server_meta_watch_worker(cardinal):
    while True:
        result = _run_server_meta_check(cardinal)
        if result is None:
            time.sleep(15)
            continue
        if result is False:
            return
        time.sleep(max(60, int(os.getenv('SDA_AUTHOR_META_CHECK_INTERVAL_SEC', '300'))))

def _start_server_meta_watch(cardinal):
    global _SERVER_META_WATCH_STARTED
    with _SERVER_META_LOCK:
        if _SERVER_META_WATCH_STARTED:
            return
        _SERVER_META_WATCH_STARTED = True
    threading.Thread(target=_server_meta_watch_worker, args=(cardinal,), name='SDA-META-SYNC', daemon=True).start()

def _tamper_restart_options():
    return max(10, int(os.getenv('SDA_TAMPER_RESTART_INTERVAL_SEC', '3600'))), max(1, int(os.getenv('SDA_TAMPER_MAX_RESTARTS', '1000')))

def _get_tamper_restart_interval(base_interval_sec, attempt):
    return max(10, int(base_interval_sec / (2 ** (max(1, int(attempt)) - 1))))

def _load_tamper_restart_state():
    with _TAMPER_RESTART_LOCK:
        default = {'restart_count': 0, 'reason': '', 'updated_at': 0}
        try:
            if not os.path.exists(_INTEGRITY_STATE_FILE):
                _save_json(_INTEGRITY_STATE_FILE, default)
                return dict(default)
            state = _load_json(_INTEGRITY_STATE_FILE)
            if not isinstance(state, dict):
                _save_json(_INTEGRITY_STATE_FILE, default)
                return dict(default)
            result = {'restart_count': max(0, int(state.get('restart_count', 0))), 'reason': str(state.get('reason') or ''), 'updated_at': max(0, int(state.get('updated_at', 0) or 0))}
            return result
        except Exception as e:
            return dict(default)

def _save_tamper_restart_state(restart_count, reason=''):
    with _TAMPER_RESTART_LOCK:
        count = max(0, int(restart_count))
        _save_json(_INTEGRITY_STATE_FILE, {'restart_count': count, 'reason': str(reason or ''), 'updated_at': int(time.time())})

def _reset_tamper_restart_state_if_clean():
    state = _load_tamper_restart_state()
    if state.get('restart_count') or state.get('reason'):
        _save_tamper_restart_state(0, '')

def _restart_cardinal_for_tamper(cardinal):
    restart = getattr(cardinal, 'restart', None)
    if callable(restart):
        try:
            logger.warning(f'{PREFIX} [ANTI-TAMPER] вызывается Cardinal.restart()')
            restart()
            time.sleep(2)
        except Exception as e:
            logger.error(f'{PREFIX} [ANTI-TAMPER] Cardinal.restart() не сработал: {e}')
    try:
        import sys
        args = list(sys.argv) or ['-m', 'FunPayCardinal']
        os.execv(sys.executable, [sys.executable] + args)
    except Exception as e:
        logger.critical(f'{PREFIX} [ANTI-TAMPER] перезапуск процесса не удался: {e}')
        return False

def _tamper_restart_worker(cardinal, immediate=False):
    base_interval, max_restarts = _tamper_restart_options()
    state = _load_tamper_restart_state()
    completed = int(state.get('restart_count', 0))
    if completed >= max_restarts:
        logger.critical(f'{PREFIX} [ANTI-TAMPER] лимит перезапусков исчерпан: {completed}/{max_restarts}')
        return
    delay = 0 if immediate else _get_tamper_restart_interval(base_interval, completed + 1)
    if delay:
        time.sleep(delay)
    current = _load_tamper_restart_state()
    completed = int(current.get('restart_count', 0))
    if completed >= max_restarts:
        return
    _save_tamper_restart_state(completed + 1, _IMMUTABLE_REASON)
    _restart_cardinal_for_tamper(cardinal)

def _start_tamper_restart_cycle(cardinal, immediate=False):
    global _TAMPER_RESTART_WORKER_STARTED
    base_interval, max_restarts = _tamper_restart_options()
    with _TAMPER_RESTART_LOCK:
        if _TAMPER_RESTART_WORKER_STARTED:
            return
        completed = int(_load_tamper_restart_state().get('restart_count', 0))
        if completed >= max_restarts:
            return
        _TAMPER_RESTART_WORKER_STARTED = True
    threading.Thread(target=_tamper_restart_worker, args=(cardinal, immediate), name='SDA-TAMPER-RESTART', daemon=True).start()

def post_start_handler(cardinal: 'Cardinal', *args):
    _patch_new_message_notifications(cardinal)

def init_cardinal(cardinal: 'Cardinal'):
    local_meta_ok = _meta_guard()
    if local_meta_ok:
        _reset_tamper_restart_state_if_clean()
    else:
        _start_tamper_restart_cycle(cardinal, False)
    _start_server_meta_watch(cardinal)
    _patch_new_message_notifications(cardinal)
    tg = cardinal.telegram
    try:
        startup_data = load_data()
        for owner_uid, accounts in (startup_data or {}).items():
            if owner_uid == 'global' or not isinstance(accounts, list):
                continue
            _log_event(str(owner_uid), 'START', f'Плагин запущен. Версия {VERSION}', accounts=len(accounts))
        logger.info(f'{PREFIX} plugin started, version={VERSION}')
    except Exception as e:
        logger.warning(f'{PREFIX} startup log failed: {e}')
    tg.msg_handler(lambda m: open_welcome(cardinal, m), commands=['sda_menu'])
    tg.msg_handler(lambda m: _handle_fsm(m, cardinal), func=lambda m: m.chat.id in _fsm, content_types=['text', 'document'])
    tg.cbq_handler(lambda c: open_welcome(cardinal, c), func=lambda c: c.data.startswith(f'{CBT_EDIT_PLUGIN}:{UUID}') or c.data.startswith(f'{CBT_PLUGIN_SETTINGS}:{UUID}') or c.data == CB_WELCOME)
    tg.cbq_handler(lambda c: open_settings(cardinal, c), func=lambda c: c.data == CB_SETTINGS)
    tg.cbq_handler(lambda c: acknowledge_instruction(cardinal, c), func=lambda c: c.data == CB_INSTRUCTION_ACK)
    tg.cbq_handler(lambda c: open_information(cardinal, c), func=lambda c: c.data == CB_INFO)
    tg.cbq_handler(lambda c: open_update_menu(cardinal, c), func=lambda c: c.data == CB_UPDATE_PLUGIN)
    tg.cbq_handler(lambda c: start_local_plugin_update(cardinal, c), func=lambda c: c.data == CB_UPDATE_PLUGIN_LOCAL)
    tg.cbq_handler(lambda c: check_online_plugin_update(cardinal, c), func=lambda c: c.data == CB_UPDATE_PLUGIN_ONLINE)
    tg.cbq_handler(lambda c: install_online_plugin_update(cardinal, c), func=lambda c: c.data == CB_UPDATE_PLUGIN_YES)
    tg.cbq_handler(lambda c: cancel_online_plugin_update(cardinal, c), func=lambda c: c.data == CB_UPDATE_PLUGIN_NO)
    tg.cbq_handler(lambda c: toggle_plugin(cardinal, c), func=lambda c: c.data == CB_PLUGIN_TOGGLE)
    tg.cbq_handler(lambda c: _start_add(cardinal, c), func=lambda c: c.data == CB_ADD)
    tg.cbq_handler(lambda c: open_list(cardinal, c, 0), func=lambda c: c.data == CB_LIST)
    tg.cbq_handler(lambda c: open_list(cardinal, c, int(c.data.split(':')[-1])), func=lambda c: c.data.startswith(f'{CB_LIST_PAGE}:'))
    tg.cbq_handler(lambda c: open_account_detail(cardinal, c), func=lambda c: c.data.startswith(f'{CB_ACCOUNT_OPEN}:'))
    tg.cbq_handler(lambda c: toggle_account_enabled(cardinal, c), func=lambda c: c.data.startswith(f'{CB_ACCOUNT_TOGGLE_ENABLED}:'))
    tg.cbq_handler(lambda c: toggle_account_queue(cardinal, c), func=lambda c: c.data.startswith(f'{CB_ACCOUNT_TOGGLE_QUEUE}:'))
    tg.cbq_handler(lambda c: toggle_account_notifications(cardinal, c), func=lambda c: c.data.startswith(f'{CB_ACCOUNT_TOGGLE_NOTIFY}:'))
    tg.cbq_handler(lambda c: start_account_command_edit(cardinal, c), func=lambda c: c.data.startswith(f'{CB_ACCOUNT_EDIT_COMMAND}:'))
    tg.cbq_handler(lambda c: open_account_text_menu(cardinal, c), func=lambda c: c.data.startswith(f'{CB_ACCOUNT_TEXT_MENU}:'))
    tg.cbq_handler(lambda c: use_account_global_text(cardinal, c), func=lambda c: c.data.startswith(f'{CB_ACCOUNT_TEXT_GLOBAL}:'))
    tg.cbq_handler(lambda c: start_account_custom_text_edit(cardinal, c), func=lambda c: c.data.startswith(f'{CB_ACCOUNT_TEXT_CUSTOM}:'))
    tg.cbq_handler(lambda c: start_account_secret_edit(cardinal, c), func=lambda c: c.data.startswith(f'{CB_ACCOUNT_EDIT_SECRET}:'))
    tg.cbq_handler(lambda c: start_account_limit_edit(cardinal, c), func=lambda c: c.data.startswith(f'{CB_ACCOUNT_EDIT_LIMIT}:'))
    tg.cbq_handler(lambda c: open_del_menu(cardinal, c), func=lambda c: c.data == CB_DEL_MENU)
    tg.cbq_handler(lambda c: start_template_edit(cardinal, c), func=lambda c: c.data == CB_TEMPLATE)
    tg.cbq_handler(lambda c: open_config_menu(cardinal, c), func=lambda c: c.data == CB_CONFIG_MENU)
    tg.cbq_handler(lambda c: export_config(cardinal, c), func=lambda c: c.data == CB_CONFIG_EXPORT)
    tg.cbq_handler(lambda c: start_config_import(cardinal, c), func=lambda c: c.data == CB_CONFIG_IMPORT)
    tg.cbq_handler(lambda c: open_account_template_menu(cardinal, c), func=lambda c: c.data == CB_ACCOUNT_TEMPLATE_MENU)
    tg.cbq_handler(lambda c: start_account_template_edit(cardinal, c, str(c.data.split(':')[-1])), func=lambda c: c.data.startswith(f'{CB_ACCOUNT_TEMPLATE_PICK}:'))
    tg.cbq_handler(lambda c: _fsm_cancel(cardinal, c), func=lambda c: c.data == CB_CANCEL)
    tg.cbq_handler(lambda c: _add_use_auto_command(cardinal, c), func=lambda c: c.data == CB_ADD_CMD_AUTO)
    tg.cbq_handler(lambda c: _add_choose_custom_command(cardinal, c), func=lambda c: c.data == CB_ADD_CMD_CUSTOM)
    tg.cbq_handler(lambda c: _add_use_global_template(cardinal, c), func=lambda c: c.data == CB_ADD_TEMPLATE_GLOBAL)
    tg.cbq_handler(lambda c: _add_choose_custom_template(cardinal, c), func=lambda c: c.data == CB_ADD_TEMPLATE_CUSTOM)
    tg.cbq_handler(lambda c: _add_choose_queue(cardinal, c, True), func=lambda c: c.data == CB_ADD_QUEUE_YES)
    tg.cbq_handler(lambda c: _add_choose_queue(cardinal, c, False), func=lambda c: c.data == CB_ADD_QUEUE_NO)
    tg.cbq_handler(lambda c: toggle_queue(cardinal, c), func=lambda c: c.data == CB_QUEUE_TOGGLE)
    tg.cbq_handler(lambda c: toggle_command_notifications(cardinal, c), func=lambda c: c.data == CB_CMD_NOTIFY_TOGGLE)
    tg.cbq_handler(lambda c: toggle_template_mode(cardinal, c), func=lambda c: c.data == CB_TEMPLATE_MODE_TOGGLE)
    tg.cbq_handler(lambda c: open_blacklist(cardinal, c), func=lambda c: c.data == CB_BL)
    tg.cbq_handler(lambda c: toggle_blacklist(cardinal, c), func=lambda c: c.data == CB_BL_TOGGLE)
    tg.cbq_handler(lambda c: toggle_blacklist_scope(cardinal, c), func=lambda c: c.data == CB_BL_SCOPE)
    tg.cbq_handler(lambda c: start_blacklist_nicks_edit(cardinal, c), func=lambda c: c.data == CB_BL_NICKS)
    tg.cbq_handler(lambda c: open_blacklist_nicks(cardinal, c, int(c.data.split(':')[-1])), func=lambda c: c.data.startswith(f'{CB_BL_NICK_PAGE}:'))
    tg.cbq_handler(lambda c: start_blacklist_nick_add(cardinal, c, int(c.data.split(':')[-1])), func=lambda c: c.data.startswith(f'{CB_BL_NICK_ADD}:'))
    tg.cbq_handler(lambda c: delete_blacklist_nick(cardinal, c, int(c.data.split(':')[-2]), int(c.data.split(':')[-1])), func=lambda c: c.data.startswith(f'{CB_BL_NICK_DEL}:'))
    tg.cbq_handler(lambda c: start_blacklist_text_edit(cardinal, c), func=lambda c: c.data == CB_BL_TEXT)
    tg.cbq_handler(lambda c: open_blacklist_accounts(cardinal, c), func=lambda c: c.data == CB_BL_ACCS)
    tg.cbq_handler(lambda c: toggle_blacklist_account(cardinal, c, str(c.data.split(':')[-1])), func=lambda c: c.data.startswith(f'{CB_BL_ACC_TOGGLE}:'))
    tg.cbq_handler(lambda c: open_del_confirm(cardinal, c, int(c.data.split(':')[-1])), func=lambda c: c.data.startswith(f'{CB_DEL_PICK}:'))
    tg.cbq_handler(lambda c: del_yes(cardinal, c, int(c.data.split(':')[-1])), func=lambda c: c.data.startswith(f'{CB_DEL_YES}:'))
    tg.cbq_handler(lambda c: del_no(cardinal, c), func=lambda c: c.data == CB_DEL_NO)
    tg.cbq_handler(lambda c: open_logs(cardinal, c, int(c.data.split(':')[-1])), func=lambda c: c.data.startswith(f'{CB_LOGS}:'))
    tg.cbq_handler(lambda c: _delete_plugin_open(cardinal, c), func=lambda c: c.data == CB_DELETE_PLUGIN)
    tg.cbq_handler(lambda c: _delete_plugin_try(cardinal, c), func=lambda c: c.data == CB_DELETE_PLUGIN_YES)
    tg.cbq_handler(lambda c: _delete_plugin_no(cardinal, c), func=lambda c: c.data == CB_DELETE_PLUGIN_NO)
    tg.cbq_handler(lambda c: open_welcome(cardinal, c), func=lambda c: c.data == CB_WELCOME)
    tg.cbq_handler(lambda c: open_welcome(cardinal, c), func=lambda c: c.data == CBT_BACK)
    try:
        cardinal.add_telegram_commands(UUID, [('sda_menu', 'Открыть меню Steam Guard (SDA)', True)])
    except Exception as e:
        logger.warning(f'{PREFIX} add_telegram_commands failed: {e}')
    try:
        q = load_queue()
        _cleanup_queue_state(q)
        save_queue(q)
        if _plugin_enabled() and _queue_enabled():
            for account_key, st in q.items():
                if not isinstance(st, dict) or not st.get('queue'):
                    continue
                _, acc, cfg = _find_live_account_by_key(account_key)
                if acc is not None and _account_queue_effective(acc, cfg):
                    _schedule_queue_processing(cardinal, account_key, _seconds_to_next_slot())
    except Exception as e:
        logger.warning(f'{PREFIX} queue init failed: {e}')
BIND_TO_PRE_INIT = [init_cardinal]
BIND_TO_NEW_MESSAGE = [new_message_handler]
BIND_TO_POST_START = [post_start_handler]
BIND_TO_DELETE = None