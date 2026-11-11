"""BFT floating CH chain: log-file input and ordinary Windows overlay only."""
import argparse
import configparser
import ctypes
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import time
import tkinter as tk
from chchain import Chain
import settings_store
from settings_hub import Hub
from logwatch import LogFollower, identity

BASE = Path(__file__).resolve().parent
RUNTIME = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'BaitAndTackle'
CONFIG = RUNTIME / 'ch_chain.json'

class Windows:
    def __init__(self):
        self.u = ctypes.WinDLL('user32', use_last_error=True)
        try:
            self.u.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
            self.u.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except (AttributeError, OSError): pass
        self.u.FindWindowW.argtypes = [W.LPCWSTR, W.LPCWSTR]; self.u.FindWindowW.restype = W.HWND
        self.u.GetForegroundWindow.restype = W.HWND
        self.u.GetClientRect.argtypes = [W.HWND, ctypes.POINTER(W.RECT)]
        self.u.ClientToScreen.argtypes = [W.HWND, ctypes.POINTER(W.POINT)]
        self.u.IsIconic.argtypes = [W.HWND]
        self.u.SetWindowPos.argtypes = [W.HWND, W.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, W.UINT]
        self.u.GetParent.argtypes = [W.HWND]; self.u.GetParent.restype = W.HWND
        get = 'GetWindowLongPtrW' if ctypes.sizeof(ctypes.c_void_p) == 8 else 'GetWindowLongW'
        put = 'SetWindowLongPtrW' if ctypes.sizeof(ctypes.c_void_p) == 8 else 'SetWindowLongW'
        self.get_style = getattr(self.u, get); self.get_style.argtypes = [W.HWND, ctypes.c_int]; self.get_style.restype = ctypes.c_ssize_t
        self.set_style = getattr(self.u, put); self.set_style.argtypes = [W.HWND, ctypes.c_int, ctypes.c_ssize_t]; self.set_style.restype = ctypes.c_ssize_t

    def game(self):
        hwnd = self.u.FindWindowW(None, 'EverQuest')
        if not hwnd or self.u.IsIconic(hwnd): return None
        rect, point = W.RECT(), W.POINT(0, 0)
        if not self.u.GetClientRect(hwnd, ctypes.byref(rect)): return None
        self.u.ClientToScreen(hwnd, ctypes.byref(point))
        return hwnd, point.x, point.y, rect.right, rect.bottom

    def clickthrough(self, root):
        hwnd = self.u.GetParent(root.winfo_id()) or root.winfo_id()
        self.set_style(hwnd, -20, self.get_style(hwnd, -20) | 0x20 | 0x80000 | 0x80 | 0x08000000)
        return hwnd

class Overlay:
    def __init__(self, args):
        self.args = args
        self.win = Windows()
        self.root = tk.Tk(); self.root.title('BFT CH Chain')
        self.root.withdraw()
        if not args.demo: self.root.overrideredirect(True)
        self.root.configure(bg='#061014'); self.root.attributes('-topmost', True)
        self.canvas = tk.Canvas(self.root, bg='#061014', height=76, highlightthickness=1, highlightbackground='#9d8545')
        self.canvas.pack(fill='both', expand=True)
        self.root.update_idletasks()
        if not args.demo: self.win.clickthrough(self.root)
        self.settings = None; self.key_was_down = False; self.beep_key = None
        self.chain = Chain(self.load())
        self.hub = Hub()
        self.character = 'Waiting for login'
        self.follower = LogFollower(args.logs_dir)
        self.last_check = 0; self.last_position = 0; self.offset = (8, 4)
        self.seen_game = False; self.gone_since = None
        self.last_error = ''
        if args.demo:
            self.chain = Chain(dict(self.chain.config, roster=['001', '002', '003', '004'], my_slot='004'))
            self.character = 'Demo character'
            self.root.geometry('1100x76'); self.root.deiconify()
            self.demo_started = time.time(); self.demo_step = -1
        self.root.after(100, self.tick)

    def load(self):
        return settings_store.load()['ch']

    def edit(self):
        self.hub.open()

    def draw(self, width, now):
        cv = self.canvas; cv.delete('all'); snap = self.chain.snapshot(now)
        gold, light, muted, teal = '#c6a650', '#eaf0e9', '#93b4b7', '#239b95'
        def text(x, y, label, color=light, font=('Consolas', 10)):
            cv.create_text(x, y, text=label, fill=color, anchor='nw', font=font)
        text(10, 5, 'CH CHAIN', gold, ('Consolas', 11, 'bold'))
        text(width - 159, 5, 'CTRL+J  SETTINGS', muted, ('Consolas', 9))
        status = self.last_error or snap['state']
        if snap['last']:
            last = snap['last']; next_slot = snap['next'] or 'SET ROSTER'
            due = f"{max(0,snap['due']):.1f}s" if snap['due'] >= 0 else f"LATE {abs(snap['due']):.1f}s"
            me = bool(snap['next'] and snap['next'] == self.chain.config['my_slot'])
            status = f"{last['slot']} {last['speaker']} > {last['target']}    NEXT {next_slot}  {due}"
            if me: status += '   YOUR NEXT'
            text(114, 5, status[:max(10, (width - 295)//8)], '#ffba62' if me or snap['state'] == 'LATE' else light)
            if me and self.chain.config['sound'] and snap['due'] <= 0:
                key = (last['started'], snap['next'])
                if self.beep_key != key:
                    self.beep_key = key
                    import winsound
                    winsound.MessageBeep(winsound.MB_OK)
        else: text(114, 5, (status + ' â€” ' + self.character)[:max(10, (width-295)//8)], muted)
        casts = snap['casts'][:max(1, min(8, width//160))]
        if casts:
            cell = (width-20)/len(casts)
            for i, cast in enumerate(casts):
                x, end = 10+i*cell, 10+(i+1)*cell-8
                cv.create_rectangle(x, 29, end, 57, fill='#10282d', outline='#25434a')
                cv.create_rectangle(x+1, 50, x+1+(end-x-2)*cast['fraction'], 56, fill=teal, outline='')
                name = f"{cast['slot']} {cast['speaker']}  {cast['remaining']:.1f}s"
                text(x+5, 30, name[:max(4, int((end-x-10)//7))], light, ('Consolas', 9))
        else: text(10, 32, 'Waiting for a matching announcement. Press Ctrl+J to set your raid format.', muted, ('Consolas', 9))
        text(10, 60, 'ESTIMATED CAST TIMERS â€” ANNOUNCEMENTS DO NOT CONFIRM HEALS', '#627e85', ('Consolas', 8))

    def tick(self):
        now = time.time(); mono = time.monotonic(); game = self.win.game()
        try:
            if self.args.demo:
                step = int((now-self.demo_started)//3)
                if step != self.demo_step:
                    self.demo_step = step
                    slot = ['001', '002', '003', '004'][step%4]
                    self.chain.consume(f"Cleric{chr(65+step%4)} shouts, '{slot} CH -- Tankname'", now)
                self.draw(max(400, self.root.winfo_width()), now)
            else:
                if mono-self.last_check >= 1:
                    self.last_check = mono
                    prefs = self.load()
                    if prefs != self.chain.config:
                        self.chain = Chain(prefs); self.beep_key = None
                    if self.follower.refresh():
                        name, server = identity(self.follower.path); self.character = name+' ['+server+']'
                        self.chain = Chain(self.chain.config); self.beep_key = None
                    if game: self.seen_game = True; self.gone_since = None
                    elif self.seen_game and self.gone_since is None: self.gone_since = mono
                    elif self.gone_since and mono-self.gone_since > 15 and not os.environ.get('BFT_MANAGED_SESSION'):
                        self.root.destroy(); return
                for line in self.follower.read_lines(): self.chain.consume(line, now, self.character.split(' [')[0])
                if game and self.win.u.GetForegroundWindow() == game[0]:
                    if mono-self.last_position > 1:
                        self.last_position = mono
                        cp = configparser.ConfigParser()
                        try:
                            cp.read(self.args.game / 'BFT_HUD/BFT_Position.ini')
                            self.offset = (cp.getint('Position', 'StripX', fallback=8), cp.getint('Position', 'StripY', fallback=4))
                        except (OSError, configparser.Error, ValueError): pass
                    hwnd, x, y, width, height = game
                    strip_width = max(1, width-16)
                    ox = min(max(0, self.offset[0]), max(0, width-strip_width))
                    oy = min(max(0, self.offset[1]+46), max(0,height-76))
                    if self.chain.config['enabled']:
                        self.root.geometry(f'{strip_width}x76'); self.win.clickthrough(self.root)
                        self.root.deiconify(); self.root.update_idletasks()
                        handle = self.win.clickthrough(self.root)
                        self.win.u.SetWindowPos(handle, ctypes.c_void_p(-1), x+ox, y+oy, strip_width, 76, 0x0010)
                        self.draw(strip_width, now)
                    else: self.root.withdraw()
                else: self.root.withdraw()
            control = bool(self.win.u.GetAsyncKeyState(0x11) & 0x8000)
            down = control and bool(self.win.u.GetAsyncKeyState(ord('J')) & 0x8000)
            if down and not self.key_was_down and (self.args.demo or (game and self.win.u.GetForegroundWindow() == game[0])): self.edit()
            self.key_was_down = down
            self.last_error = ''
        except (OSError, ValueError) as e:
            self.last_error = 'LOG ERROR: '+str(e)[:80]
        self.root.after(100, self.tick)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--game', type=Path, default=BASE.parent)
    parser.add_argument('--logs-dir', type=Path)
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--settings', action='store_true')
    args = parser.parse_args(); args.logs_dir = args.logs_dir or args.game/'Logs'
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, W.BOOL, W.LPCWSTR]; kernel.CreateMutexW.restype = W.HANDLE
    kernel.CloseHandle.argtypes = [W.HANDLE]
    mutex = kernel.CreateMutexW(None, False, r'Local\BFT_CH_Overlay_Demo' if args.demo else r'Local\BFT_CH_Overlay')
    if not mutex: raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == 183:
        kernel.CloseHandle(mutex); return
    try:
        app = Overlay(args)
        def report_error(kind, value, trace):
            import traceback
            RUNTIME.mkdir(parents=True, exist_ok=True)
            with (RUNTIME/'ch_overlay.log').open('a', encoding='utf-8') as f:
                traceback.print_exception(kind, value, trace, file=f)
        app.root.report_callback_exception = report_error
        if args.settings: app.root.after(300, app.edit)
        try: app.root.mainloop()
        finally:
            app.follower.close()
            app.hub.close()
    finally: kernel.CloseHandle(mutex)

if __name__ == '__main__':
    try: main()
    except Exception:
        import traceback
        RUNTIME.mkdir(parents=True, exist_ok=True)
        with (RUNTIME/'ch_overlay.log').open('a', encoding='utf-8') as f: traceback.print_exc(file=f)
        raise
