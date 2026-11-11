"""Start the log feed and EverQuest as one session; stop the feed on exit."""
import ctypes
from ctypes import wintypes
import json
import hashlib
import atexit
import os
from pathlib import Path
import subprocess
import sys
import time
from process_check import find_game_processes
from session_lifecycle import HelperJob, k, process_path

base = Path(__file__).resolve().parent
game = base.parent
if not (game / 'eqgame.exe').is_file():
    game = Path(r'C:\EverQuest Project 1999')
    base = game / 'BFT_HUD'
runtime = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'BaitAndTackle'
runtime.mkdir(parents=True, exist_ok=True)

def alert(text):
    ctypes.windll.user32.MessageBoxW(None, text, 'Bait & Tackle', 0x10)

class SHELLEXECUTEINFO(ctypes.Structure):
    _fields_ = [('cbSize', wintypes.DWORD), ('fMask', ctypes.c_ulong),
        ('hwnd', wintypes.HWND), ('lpVerb', wintypes.LPCWSTR),
        ('lpFile', wintypes.LPCWSTR), ('lpParameters', wintypes.LPCWSTR),
        ('lpDirectory', wintypes.LPCWSTR), ('nShow', ctypes.c_int),
        ('hInstApp', wintypes.HINSTANCE), ('lpIDList', ctypes.c_void_p),
        ('lpClass', wintypes.LPCWSTR), ('hkeyClass', wintypes.HKEY),
        ('dwHotKey', wintypes.DWORD), ('hIcon', wintypes.HANDLE), ('hProcess', wintypes.HANDLE)]

def main():
    # Run both halves under the same token. The game already requests admin
    # access; elevating the launcher first avoids splitting feed/game contexts.
    if not ctypes.windll.shell32.IsUserAnAdmin():
        if '--elevated' in sys.argv:
            raise RuntimeError('Windows administrator permission was not granted.')
        command = subprocess.list2cmdline([str(Path(__file__).resolve()), '--elevated'])
        result = ctypes.windll.shell32.ShellExecuteW(None, 'runas', sys.executable,
            command, str(Path(__file__).resolve().parent), 0)
        if result <= 32:
            raise RuntimeError('Windows did not authorize starting Bait & Tackle.')
        return
    k.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    k.CreateMutexW.restype = wintypes.HANDLE
    session_mutex = k.CreateMutexW(None, False, 'Local\\BFT_Session_' + hashlib.sha256(str(game.resolve()).casefold().encode()).hexdigest()[:24])
    if not session_mutex: raise ctypes.WinError(ctypes.get_last_error())
    already_running = ctypes.get_last_error() == 183
    atexit.register(k.CloseHandle, session_mutex)
    if already_running: return
    config = json.loads((base / 'config.json').read_text())
    log = Path(config.get('log', str(game / 'Logs/eqlog_Character_Server.txt')))
    automatic = config.get('auto_detect', True)
    logs_dir = Path(config.get('logs_dir', str(game / 'Logs')))
    if automatic and not logs_dir.is_dir():
        alert('The EverQuest Logs folder was not found:\n' + str(logs_dir))
        return
    if not automatic and not log.is_file():
        alert('The configured character log was not found:\n' + str(log))
        return
    executable = (game / 'eqgame.exe').resolve()
    matches = find_game_processes(executable)
    if len(matches) > 1:
        raise RuntimeError('More than one EverQuest session is open from this folder. Close the extra session first.')
    python = Path(sys.executable)
    if python.with_name('pythonw.exe').is_file(): python = python.with_name('pythonw.exe')
    owner = None
    handle = None
    job = HelperJob()
    try:
        if matches:
            handle = k.OpenProcess(0x101000, False, matches[0])
            if not handle: raise ctypes.WinError(ctypes.get_last_error())
            if Path(process_path(handle)).resolve() != executable:
                raise RuntimeError('The selected EverQuest process changed. Try again.')
        else:
            owner = subprocess.Popen([str(executable), 'patchme'], cwd=game)
            handle = owner._handle
        os.environ['BFT_MANAGED_SESSION'] = '1'
        feed_args = ['--auto', '--logs-dir', str(logs_dir)] if automatic else ['--log', str(log)]
        job.start([str(python), str(base / 'feeder.py'), *feed_args], base)
        job.start([str(python), str(base / 'ch_overlay.py'), '--game', str(game),
            '--logs-dir', str(logs_dir)], base)
        # Wait on this exact process, including while minimized. No permanent watcher.
        k.WaitForSingleObject(handle, 0xffffffff)
    finally:
        # Closing the job also stops owned browser descendants, even after a launcher crash.
        job.close()
        if handle and owner is None: k.CloseHandle(handle)

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        alert(str(exc))
