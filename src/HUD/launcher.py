"""Start the log feed and EverQuest as one session; stop the feed on exit."""
import ctypes
from ctypes import wintypes
import json
import sqlite3
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

def apply_layouts():
    try:
        if find_game_processes():return
        from layout_tools import LayoutService
        LayoutService(game,runtime/'layouts').apply_pending()
        from vision_fix import VisionFix
        VisionFix(game,runtime).apply_pending()
    except (OSError,ValueError,TypeError,KeyError) as exc:
        try:(runtime/'layout-errors.log').write_text(str(exc),encoding='utf-8')
        except OSError:pass

def game_identity(handle):
    created=wintypes.FILETIME();ended=wintypes.FILETIME();kernel=wintypes.FILETIME();user=wintypes.FILETIME()
    k.GetProcessTimes.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.FILETIME),ctypes.POINTER(wintypes.FILETIME),ctypes.POINTER(wintypes.FILETIME),ctypes.POINTER(wintypes.FILETIME)]
    if k.GetProcessTimes(handle,ctypes.byref(created),ctypes.byref(ended),ctypes.byref(kernel),ctypes.byref(user)):
        return str((created.dwHighDateTime<<32)|created.dwLowDateTime)
    import uuid
    return uuid.uuid4().hex

def main():
    attach_only = '--attach-only' in sys.argv
    game_pid = None
    if '--game-pid' in sys.argv:
        index = sys.argv.index('--game-pid')
        if index+1 >= len(sys.argv): raise ValueError('Missing EverQuest process ID.')
        game_pid = int(sys.argv[index+1])
        if game_pid <= 0: raise ValueError('Invalid EverQuest process ID.')
        attach_only = True
    # Run both halves under the same token. The game already requests admin
    # access; elevating the launcher first avoids splitting feed/game contexts.
    if not attach_only and not ctypes.windll.shell32.IsUserAnAdmin():
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
    from game_window import game_window,window_alive
    visible=game_window(executable,game_pid)
    matches = [game_pid] if game_pid else ([visible['pid']] if visible else find_game_processes(executable))
    if attach_only and not matches:return
    if len(matches) > 1:
        raise RuntimeError('More than one EverQuest session is open from this folder. Close the extra session first.')
    python = Path(sys.executable)
    if python.with_name('pythonw.exe').is_file(): python = python.with_name('pythonw.exe')
    owner = None
    handle = None
    game_finished = False
    window_watch = None
    selected_pid = None
    job = HelperJob()
    try:
        if matches:
            selected_pid=matches[0]
            # No query or VM access is necessary to watch an already-open game.
            handle=k.OpenProcess(0x100000,False,selected_pid)
            if handle:
                if k.WaitForSingleObject(handle,0)==0:return
            else:
                if not visible:raise RuntimeError('EQ denied a wait handle and no verified EQ window is available.')
                window_watch=visible['hwnd']
        else:
            pending = base / 'pending-autostart.bin'
            if pending.is_file():
                import shutil
                shutil.copy2(pending, base / 'BFT_HUD.addon32')
                pending.unlink()
            apply_layouts()
            owner = subprocess.Popen([str(executable), 'patchme'], cwd=game)
            handle = owner._handle
            selected_pid = owner.pid
        os.environ['BFT_MANAGED_SESSION'] = '1'
        session_path=runtime/('session-'+hashlib.sha256(str(game.resolve()).casefold().encode()).hexdigest()[:20]+'.json')
        try:previous=json.loads(session_path.read_text(encoding='utf-8'))
        except (OSError,ValueError):previous={}
        if visible and previous.get('active') and previous.get('pid')==selected_pid and previous.get('hwnd') in [None,visible['hwnd']]:session_id=previous['token']
        else:session_id=game_identity(handle) if handle else 'window-'+str(selected_pid)+'-'+str(window_watch)
        session_path.write_text(json.dumps({'pid':selected_pid,'hwnd':visible['hwnd'] if visible else None,'token':session_id,'active':True}),encoding='utf-8')
        os.environ['BFT_GAME_SESSION']=session_id
        feed_args = ['--auto', '--logs-dir', str(logs_dir)] if automatic else ['--log', str(log)]
        job.start([str(python), str(base / 'feeder.py'), *feed_args], base)
        job.start([str(python), str(base / 'ch_overlay.py'), '--game', str(game),
            '--logs-dir', str(logs_dir), *(['--settings'] if '--settings' in sys.argv else [])], base)
        # Wait on this exact process, including while minimized. No permanent watcher.
        if handle:game_finished=k.WaitForSingleObject(handle,0xffffffff)==0
        else:
            missing=None
            while True:
                if window_alive(window_watch,selected_pid):missing=None
                else:
                    replacement=game_window(executable,selected_pid)
                    if replacement:window_watch=replacement['hwnd'];missing=None
                    elif missing is None:missing=time.monotonic()
                    elif time.monotonic()-missing>=3:game_finished=True;break
                time.sleep(.25)
    finally:
        # Closing the job also stops owned browser descendants, even after a launcher crash.
        job.close()
        if game_finished:
            try:session_path.write_text(json.dumps({'active':False}),encoding='utf-8')
            except OSError:pass
            from experience import finish_game,database_path
            try:finish_game(database_path(game,runtime),session_id)
            except (OSError,sqlite3.Error):pass
            apply_layouts()
        if handle and owner is None: k.CloseHandle(handle)

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        alert(str(exc))
