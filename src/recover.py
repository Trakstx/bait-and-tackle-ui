"""Restore one verified file-set journal; never touch unrelated files or saved incidents."""
import argparse,json,os
from pathlib import Path
from process_check import is_game_running
from file_transaction import FileTransaction

def desktop_path():
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as key:
        return Path(os.path.expandvars(winreg.QueryValueEx(key,'Desktop')[0]))

def main():
    p=argparse.ArgumentParser();p.add_argument('--game',type=Path);p.add_argument('--journal',type=Path);a=p.parse_args()
    if is_game_running():raise RuntimeError('Close every EverQuest session before recovery.')
    if not a.game or not a.journal:
        import tkinter as tk
        from tkinter import filedialog
        root=tk.Tk();root.withdraw()
        game=str(a.game) if a.game else filedialog.askdirectory(title='Choose the EQ folder to restore')
        journal=str(a.journal) if a.journal else filedialog.askopenfilename(title='Choose the recovery journal.json',filetypes=[('Recovery journal','journal.json')])
        root.destroy()
        if not game or not journal:return
        a.game=Path(game);a.journal=Path(journal)
    if not (a.game/'eqgame.exe').is_file():raise ValueError('Choose an EverQuest installation.')
    directory=a.journal if a.journal.is_dir() else a.journal.parent
    FileTransaction.restore(directory,[a.game,desktop_path()])
    print('Restored the recorded file set. Logs, personal preferences and saved incidents were not selected for deletion.')
if __name__=='__main__':
    try:main()
    except Exception as e:print('RECOVERY STOPPED:',e);raise SystemExit(1)
