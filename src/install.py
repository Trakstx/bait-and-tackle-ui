"""Local, manifest-verified Bait & Tackle installer with backups."""
import argparse
import ctypes
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
from process_check import is_game_running

ROOT = Path(__file__).resolve().parent
SKIN = 'BAIT_AND_FUCKING_TACLE'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verified_payload():
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    result = []
    for relative, expected in manifest['files'].items():
        if not isinstance(relative,str) or '\\' in relative or ':' in relative or '..' in PurePosixPath(relative).parts or PurePosixPath(relative).is_absolute():raise ValueError('Unsafe payload path.')
        from file_transaction import checked
        source = checked(ROOT/'payload'/relative,[ROOT/'payload'])
        source.relative_to((ROOT / 'payload').resolve())
        if not source.is_file() or digest(source) != expected:
            raise RuntimeError('Package is incomplete or changed: ' + relative)
        result.append((relative, source))
    return result

def desktop_path():
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as key:
        return Path(os.path.expandvars(winreg.QueryValueEx(key, 'Desktop')[0]))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--game', default=r'C:\EverQuest Project 1999')
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--elevated', action='store_true')
    parser.add_argument('--restore', type=Path, help='Restore a verified recovery journal with EQ closed')
    parser.add_argument('--no-shortcut', action='store_true')
    args = parser.parse_args()
    files = verified_payload()
    if args.verify:
        print('Package verified:', len(files), 'files. No installation performed.')
        return
    game = Path(args.game).resolve()
    if not (game / 'eqgame.exe').is_file():
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw()
        selected = filedialog.askdirectory(title='Select the EverQuest folder containing eqgame.exe', parent=root)
        root.destroy()
        if not selected: raise RuntimeError('No EverQuest folder was selected.')
        game = Path(selected).resolve()
        if not (game / 'eqgame.exe').is_file(): raise RuntimeError('The selected folder does not contain eqgame.exe.')
    if is_game_running():
        raise RuntimeError('Close EverQuest before installing.')
    # Only the installation write operation may request elevation, and only when required.
    writable = True
    for relative, source in files:
        parent = (game / relative).parent
        while not parent.exists(): parent = parent.parent
        try:
            with tempfile.TemporaryFile(dir=parent): pass
        except PermissionError:
            writable = False; break
    if not writable and not ctypes.windll.shell32.IsUserAnAdmin():
        if args.elevated:
            raise RuntimeError('Administrator access was not granted.')
        command = subprocess.list2cmdline([str(Path(__file__).resolve()), '--game', str(game), '--elevated', *(['--restore',str(args.restore)] if args.restore else []), *(['--no-shortcut'] if args.no_shortcut else [])])
        result = ctypes.windll.shell32.ShellExecuteW(None, 'runas', sys.executable, command, str(ROOT), 1)
        if result <= 32:
            raise RuntimeError('Windows did not authorize installation.')
        print('Continue in the installer window opened by Windows.')
        return
    # Refuse to collide with somebody else's graphics hook or ReShade configuration.
    owned = game / 'BFT_HUD/package-installed.json'
    prior = json.loads(owned.read_text()) if owned.is_file() else {'files': {}}
    for relative in ['dxgi.dll', 'ReShade.ini', 'BFT_Test.ini']:
        destination = game / relative
        incoming = ROOT / 'payload' / relative
        if owned.is_file() and relative in ('ReShade.ini', 'BFT_Test.ini', 'BFT_HUD/BFT_Position.ini', 'BFT_HUD/threat_config.json') and destination.exists():
            continue  # Preserve ReShade's own saved settings on an upgrade.
        if destination.exists() and digest(destination) != digest(incoming):
            if relative not in prior['files'] or digest(destination) != prior['files'][relative]:
                raise RuntimeError('An unrelated or modified file already exists: ' + relative +
                    '\nIt was not overwritten.')
    from file_transaction import FileTransaction
    recovery=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'BaitAndTackle/recovery'/hashlib.sha256(str(game).casefold().encode()).hexdigest()[:20]
    shortcut=desktop_path()/'Play Bait and Tackle.cmd'
    roots=[game,shortcut.parent]
    if args.restore:
        FileTransaction.restore(args.restore,roots)
        print('Recovery completed; personal settings and saved incidents were not targeted.')
        return
    FileTransaction.recover_pending(recovery,roots)
    transaction=FileTransaction(recovery,roots);installed={}
    preserve={'ReShade.ini','BFT_Test.ini','BFT_HUD/threat_config.json'}
    for relative,source in files:
        destination=game/relative
        if owned.is_file() and relative in preserve and destination.exists():
            installed[relative]=digest(destination);continue
        raw=source.read_bytes();installed[relative]=hashlib.sha256(raw).hexdigest()
        if not destination.exists() or digest(destination)!=installed[relative]:transaction.add(destination,raw)
    # Remove only unchanged files owned by the previous package. Never retain old runtime code.
    for relative,expected in prior.get('files',{}).items():
        if relative in installed:continue
        if not isinstance(relative,str) or '\\' in relative or ':' in relative or '..' in PurePosixPath(relative).parts or PurePosixPath(relative).is_absolute():raise ValueError('Unsafe previous ownership path.')
        from file_transaction import checked
        destination=checked(game/relative,[game])
        if destination.is_file():
            if digest(destination)!=expected:raise RuntimeError('Modified obsolete managed file requires review: '+relative)
            transaction.add(destination,None)
    config=game/'BFT_HUD/config.json'
    settings=json.loads(config.read_text()) if config.is_file() else {}
    settings.update({'auto_detect':True,'logs_dir':str(game/'Logs'),'skin':SKIN});settings.setdefault('pet_names_by_character',{})
    transaction.add(config,json.dumps(settings,indent=2).encode())
    transaction.add(owned,json.dumps({'version':'0.7.1-candidate','files':installed,'backup':str(transaction.directory)},indent=2).encode())
    if not args.no_shortcut:transaction.add(shortcut,('@echo off\nstart "" "'+str(game/'BFT_HUD/Play Bait and Tackle.exe')+'"\n').encode())
    backup=transaction.commit()
    print('\nInstalled Bait & Tackle UI and HUD prototype.')
    if not args.no_shortcut:print('Desktop launcher:', shortcut)
    print('Backups:', backup)
    print('Damage strip: automatic character/log switching; rolling/fight DPS; history. Generic magic remains unassigned.')
    print('CH chain: floating log-based strip below DPS; Ctrl+J opens announcement and timing settings.')
    input('\nPress Enter to close.')

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('\nINSTALLATION STOPPED:', exc)
        if '--verify' not in sys.argv:
            input('\nPress Enter to close.')
        sys.exit(1)
