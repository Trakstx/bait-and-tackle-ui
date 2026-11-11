"""Start the log feed and EverQuest as one session; stop the feed on exit."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from process_check import is_game_running

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
    attach = is_game_running()
    python = Path(sys.executable)
    pythonw = python.with_name('pythonw.exe')
    if pythonw.is_file():
        python = pythonw
    with (runtime / 'feed.log').open('a') as output:
        feed_args = ['--auto', '--logs-dir', str(logs_dir)] if automatic else ['--log', str(log)]
        feed = subprocess.Popen([str(python), str(base / 'feeder.py'), *feed_args],
            cwd=base, stdout=output, stderr=output, creationflags=subprocess.CREATE_NO_WINDOW)
        chain = None
        try:
            chain = subprocess.Popen([str(python), str(base / 'ch_overlay.py'), '--game', str(game),
                '--logs-dir', str(logs_dir)], cwd=base, stdout=output, stderr=output,
                creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(0.5)
            if feed.poll() not in (None, 0):
                raise RuntimeError('The log feed could not start. See ' + str(runtime / 'feed.log'))
            if attach:
                # Reconnect to an already-open game without launching a second copy.
                while is_game_running():
                    time.sleep(1)
                return
            info = SHELLEXECUTEINFO()
            info.cbSize = ctypes.sizeof(info)
            info.fMask = 0x40  # SEE_MASK_NOCLOSEPROCESS
            info.lpVerb = 'open'
            info.lpFile = str(game / 'eqgame.exe')
            info.lpParameters = 'patchme'
            info.lpDirectory = str(game)
            info.nShow = 1
            shell = ctypes.WinDLL('shell32', use_last_error=True)
            shell.ShellExecuteExW.argtypes = [ctypes.POINTER(SHELLEXECUTEINFO)]
            shell.ShellExecuteExW.restype = wintypes.BOOL
            if not shell.ShellExecuteExW(ctypes.byref(info)):
                raise ctypes.WinError(ctypes.get_last_error())
            if info.hProcess:
                kernel = ctypes.WinDLL('kernel32', use_last_error=True)
                kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
                kernel.CloseHandle.argtypes = [wintypes.HANDLE]
                kernel.WaitForSingleObject(info.hProcess, 0xFFFFFFFF)
                kernel.CloseHandle(info.hProcess)
        finally:
            if chain is not None and chain.poll() is None:
                chain.terminate()
                chain.wait(timeout=5)
            if feed.poll() is None:
                feed.terminate()
                feed.wait(timeout=5)

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        alert(str(exc))
