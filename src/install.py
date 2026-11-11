"""Local, manifest-verified Bait & Tackle installer with backups."""
import argparse
import ctypes
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from process_check import is_game_running

ROOT = Path(__file__).resolve().parent
SKIN = 'BAIT_AND_FUCKING_TACLE'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verified_payload():
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    result = []
    for relative, expected in manifest['files'].items():
        source = (ROOT / 'payload' / relative).resolve()
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
    if not ctypes.windll.shell32.IsUserAnAdmin():
        if args.elevated:
            raise RuntimeError('Administrator access was not granted.')
        command = subprocess.list2cmdline([str(Path(__file__).resolve()), '--game', str(game), '--elevated'])
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
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup = game / 'BFT_HUD/backups' / stamp
    def preserve(path):
        if path.is_file():
            save = backup / path.relative_to(game)
            save.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, save)
    installed = {}
    for relative, source in files:
        destination = game / relative
        destination.resolve().relative_to(game)
        if owned.is_file() and relative in ('ReShade.ini', 'BFT_Test.ini') and destination.exists():
            installed[relative] = digest(destination)
            continue
        if not destination.exists() or digest(destination) != digest(source):
            preserve(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        if digest(destination) != digest(source):
            raise RuntimeError('Installed file failed verification: ' + relative)
        installed[relative] = digest(source)
    config = game / 'BFT_HUD/config.json'
    preserve(config)
    settings = json.loads(config.read_text()) if config.is_file() else {}
    settings.update({'auto_detect': True, 'logs_dir': str(game / 'Logs'), 'skin': SKIN})
    settings.setdefault('pet_names_by_character', {})
    config.write_text(json.dumps(settings, indent=2))
    owned.write_text(json.dumps({'version': '0.6.1-settings-hub', 'files': installed,
        'backup': str(backup)}, indent=2))
    launcher = game / 'BFT_HUD/launcher.py'
    pythonw = game / 'BFT_HUD/runtime/pythonw.exe'
    if not pythonw.is_file():
        pythonw = Path(sys.executable).with_name('pythonw.exe')
        if not pythonw.is_file(): pythonw = Path(sys.executable)
    shortcut = desktop_path() / 'Play Bait and Tackle.cmd'
    # Preserve any existing shortcut in this user's Documents backup directory.
    if shortcut.exists():
        backup.mkdir(parents=True, exist_ok=True)
        shutil.copy2(shortcut, backup / 'Play Bait and Tackle.cmd')
    shortcut.write_text('@echo off\nstart "" "' + str(pythonw) + '" "' + str(launcher) + '"\n')
    print('\nInstalled Bait & Tackle UI and HUD prototype.')
    print('Desktop launcher:', shortcut)
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
