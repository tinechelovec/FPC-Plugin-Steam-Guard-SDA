from __future__ import annotations
import os, re, html, shutil, logging, hashlib
from urllib.request import Request, urlopen

NAME = 'SDA-Temp-Updater'
VERSION = '1.0.0'
DESCRIPTION = 'Временный мини-плагин для обновления Steam Guard (SDA) командой /update_sda.'
CREDITS = '@tinechelovec'
UUID = '4ff3f19c-7ec2-4664-900b-a1f5df4f7ec3'
SETTINGS_PAGE = False

TARGET_NAME = 'Steam Guard (SDA)'
TARGET_UUID = 'b886288e-7908-4f62-bd48-48e1a5c7a8e5'
TARGET_UUID_B64 = 'Yjg4NjI4OGUtNzkwOC00ZjYyLWJkNDgtNDhlMWE1YzdhOGU1'
UPDATE_URL = os.getenv('SDA_PLUGIN_UPDATE_URL', 'https://raw.githubusercontent.com/tinechelovec/FPC-Plugin-Telegram-Stars/main/Steam-Guard-SDA/Steam-Guard-SDA.py').strip()

log = logging.getLogger(NAME)

def _h(value):
    return html.escape(str(value), quote=False)

def _send(bot, chat_id, text):
    try:
        return bot.send_message(chat_id, text, parse_mode='HTML', disable_web_page_preview=True)
    except TypeError:
        return bot.send_message(chat_id, text, parse_mode='HTML')

def _version(source):
    match = re.search(r'(?m)^\s*VERSION\s*=\s*["\']([^"\']+)["\']', source or '')
    return match.group(1).strip() if match else None

def _read(path):
    with open(path, 'r', encoding='utf-8-sig') as file:
        return file.read()

def _is_target(source):
    if not source or TARGET_NAME not in source or 'def init_cardinal' not in source:
        return False
    return TARGET_UUID in source or TARGET_UUID_B64 in source

def _candidate_dirs():
    here = os.path.dirname(os.path.abspath(__file__))
    dirs = [here, os.getcwd(), os.path.join(os.getcwd(), 'storage', 'plugins'), os.path.dirname(here)]
    result = []
    for directory in dirs:
        directory = os.path.abspath(directory)
        if os.path.isdir(directory) and directory not in result:
            result.append(directory)
    return result

def _find_target():
    env_path = os.getenv('SDA_PLUGIN_FILE', '').strip()
    self_file = os.path.abspath(__file__)
    checked = set()
    priority = [os.path.abspath(env_path)] if env_path else []
    for directory in _candidate_dirs():
        priority.extend([os.path.join(directory, 'SteamGuardSDA.py'), os.path.join(directory, 'Steam-Guard-SDA.py'), os.path.join(directory, 'steam_guard_sda.py')])
    for path in priority:
        if path in checked or path == self_file or not os.path.isfile(path):
            continue
        checked.add(path)
        try:
            if _is_target(_read(path)):
                return path
        except Exception:
            pass
    for directory in _candidate_dirs():
        try:
            for root, subdirs, files in os.walk(directory):
                if root.count(os.sep) - directory.count(os.sep) > 2:
                    subdirs[:] = []
                    continue
                for filename in files:
                    if not filename.endswith('.py'):
                        continue
                    path = os.path.abspath(os.path.join(root, filename))
                    if path in checked or path == self_file:
                        continue
                    checked.add(path)
                    try:
                        if _is_target(_read(path)):
                            return path
                    except Exception:
                        pass
        except Exception:
            pass
    raise RuntimeError('не найден установленный Steam Guard (SDA). Путь можно указать через SDA_PLUGIN_FILE')

def _download():
    if not UPDATE_URL.lower().startswith('https://'):
        raise RuntimeError('ссылка обновления должна использовать HTTPS')
    request = Request(UPDATE_URL, headers={'Accept': 'text/plain, */*;q=0.1', 'User-Agent': f'{NAME}/{VERSION}', 'Cache-Control': 'no-cache'})
    with urlopen(request, timeout=60) as response:
        payload = response.read(5 * 1024 * 1024 + 1)
    if len(payload) < 10000:
        raise RuntimeError(f'сервер вернул слишком маленький файл ({len(payload)} байт)')
    if len(payload) > 5 * 1024 * 1024:
        raise RuntimeError('файл обновления слишком большой')
    try:
        source = payload.decode('utf-8-sig')
    except UnicodeDecodeError as error:
        raise RuntimeError(f'файл обновления не UTF-8: {error}') from error
    if '<html' in source[:700].lower() or '<!doctype' in source[:700].lower():
        raise RuntimeError('вместо Python-файла скачалась HTML-страница')
    missing = [value for value in (TARGET_NAME, 'def init_cardinal', 'BIND_TO_PRE_INIT', 'BIND_TO_NEW_MESSAGE') if value not in source]
    if missing:
        raise RuntimeError('скачан не тот файл: нет ' + ', '.join(missing))
    if not _is_target(source):
        raise RuntimeError('UUID скачанного Steam Guard (SDA) не совпадает')
    new_version = _version(source)
    if not new_version:
        raise RuntimeError('в скачанном файле не найдена VERSION')
    return source, new_version, payload

def _cleanup_pyc(path):
    try:
        base = os.path.splitext(os.path.basename(path))[0]
        cache = os.path.join(os.path.dirname(path), '__pycache__')
        if os.path.isdir(cache):
            for filename in os.listdir(cache):
                if filename.startswith(base + '.') and filename.endswith('.pyc'):
                    os.remove(os.path.join(cache, filename))
    except Exception:
        pass

def _atomic_replace(path, payload):
    temp = path + '.sda_update_tmp'
    with open(temp, 'wb') as file:
        file.write(payload)
        file.flush()
        os.fsync(file.fileno())
    try:
        os.chmod(temp, os.stat(path).st_mode)
    except Exception:
        pass
    os.replace(temp, path)
    _cleanup_pyc(path)

def _delete_self():
    if os.getenv('SDA_UPDATER_KEEP_SELF', '0').strip().lower() in ('1', 'true', 'yes', 'on'):
        return 'оставлен по SDA_UPDATER_KEEP_SELF'
    self_file = os.path.abspath(__file__)
    try:
        _cleanup_pyc(self_file)
        os.remove(self_file)
        return 'удалён'
    except Exception as error:
        return f'не удалён автоматически: {_h(error)}'

def _cmd_update(cardinal, message):
    bot, chat_id = cardinal.telegram.bot, message.chat.id
    try:
        target = _find_target()
        old_payload = open(target, 'rb').read()
        old_source = old_payload.decode('utf-8-sig')
        old_version = _version(old_source) or 'не найдена'
        _send(bot, chat_id, f'⏬ <b>Проверяю обновление Steam Guard (SDA)…</b>\n\nТекущая версия: <b>{_h(old_version)}</b>')
        new_source, new_version, new_payload = _download()
        compile(new_source, target, 'exec')
        if hashlib.sha256(old_payload).digest() == hashlib.sha256(new_payload).digest():
            _send(bot, chat_id, f'✅ <b>Обновление не требуется.</b>\n\nУстановлена версия: <b>{_h(old_version)}</b>\nОнлайн-версия: <b>{_h(new_version)}</b>\nФайлы полностью совпадают.')
            return
        stamp = __import__('time').strftime('%Y%m%d-%H%M%S')
        backup = target + f'.pre-temp-update.{stamp}.bak'
        shutil.copy2(target, backup)
        _atomic_replace(target, new_payload)
        self_status = _delete_self()
        _send(bot, chat_id, '✅ <b>Steam Guard (SDA) обновлён.</b>\n\n'
              f'Версия: <b>{_h(old_version)}</b> → <b>{_h(new_version)}</b>\n'
              f'🛟 Резервная копия: <code>{_h(os.path.basename(backup))}</code>\n'
              '💾 Аккаунты, конфиг, логи и очередь сохранены.\n'
              f'🧹 Временный updater: <code>{self_status}</code>\n\n'
              '🔁 Теперь выполните <code>/restart</code>.')
    except Exception as error:
        log.exception('SDA update failed')
        try:
            _send(bot, chat_id, f'❌ <b>Не удалось обновить Steam Guard (SDA).</b>\n\nОшибка: <code>{_h(error)}</code>\n\nТекущий файл и данные не изменены.')
        except Exception:
            pass

def init_cardinal(cardinal):
    try:
        cardinal.add_telegram_commands(UUID, [('update_sda', 'Обновить Steam Guard (SDA)', True)])
    except Exception:
        pass
    cardinal.telegram.msg_handler(lambda message: _cmd_update(cardinal, message), commands=['update_sda'])
    log.info('SDA temporary updater loaded. Command: /update_sda')

BIND_TO_PRE_INIT = [init_cardinal]
BIND_TO_NEW_MESSAGE = []
BIND_TO_NEW_ORDER = []
BIND_TO_DELETE = None
