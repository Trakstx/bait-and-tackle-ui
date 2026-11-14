"""BFT floating CH chain: log-file input and ordinary Windows overlay only."""
import argparse
import configparser
import ctypes
from ctypes import wintypes as W
import json
import sqlite3
import os
from pathlib import Path
import time
import tkinter as tk
from chchain import Chain
from buff_timers import BuffTimers,spell_catalog
from buff_overlay import BuffOverlay
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
        self.u.SetLayeredWindowAttributes.argtypes = [W.HWND, W.DWORD, ctypes.c_ubyte, W.DWORD]
        self.u.SetLayeredWindowAttributes.restype = W.BOOL
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
        # A layered HWND is invisible until its alpha or color key is initialized.
        if not self.u.SetLayeredWindowAttributes(hwnd, 0, 255, 2):
            raise ctypes.WinError(ctypes.get_last_error())
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
        self.misc = settings_store.load()['misc']
        self.settings = None; self.key_was_down = False; self.beep_key = None
        self.chain = Chain(self.load())
        self.buffs = BuffTimers(spell_catalog(args.game/'spells_us.txt'),settings_store.load()['buffs'],state_dir=RUNTIME/'buff-state')
        self.buff_overlay = BuffOverlay(self.root,self.win,args.game)
        self.hub = Hub(game=args.game)
        self.hub.buff_engine = self.buffs
        self.speech=self.hub.speech
        from class_triggers import TriggerEngine
        from trigger_overlay import TriggerOverlay
        self.triggers=TriggerEngine(settings_store.load()['triggers'],RUNTIME/'trigger-profiles')
        self.hub.trigger_engine=self.triggers
        from event_timers import Timers
        import hashlib
        scope=hashlib.sha256(str(args.game.resolve()).casefold().encode()).hexdigest()[:16]
        self.timers=Timers(settings_store.load()['timers'],RUNTIME/'event-timers'/scope);self.hub.timers=self.timers
        from timer_panel import TimerPanel
        self.timer_overlay=TimerPanel(self.root,self.win,self.save_timer_position,self.save_timer_panel)
        self.trigger_overlay=TriggerOverlay(self.root,self.win,self.save_trigger_position)
        from experience import ExperienceTracker,database_path
        self.experience=ExperienceTracker(database_path(args.game,RUNTIME),os.environ.get('BFT_GAME_SESSION','unmanaged-'+str(os.getpid())))
        self.hub.experience=self.experience
        self.xp_replayed_to=0
        from eq_maps import MapTracker
        self.maps = MapTracker(self.hub.map_catalog)
        self.hub.map_tracker = self.maps
        self.character = 'Waiting for login'
        self.follower = LogFollower(args.logs_dir)
        self.last_check = 0; self.last_position = 0; self.offset = (8, 4)
        self.seen_game = False; self.gone_since = None
        self.last_error = ''; self.last_buff_status = 0; self.buff_replayed_to = 0
        if args.demo:
            self.chain = Chain(dict(self.chain.config, roster=['001', '002', '003', '004'], my_slot='004'))
            self.character = 'Demo character'
            self.root.geometry('1100x76'); self.root.deiconify()
            self.demo_started = time.time(); self.demo_step = -1
        self.root.after(100, self.tick)

    def save_trigger_position(self,x,y):
        with self.hub.lock:
            data=settings_store.load();data['triggers'].update(x=x,y=y,move_mode=False);settings_store.save(data);self.triggers.configure(data['triggers'])

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
        else: text(114, 5, (status + ' — ' + self.character)[:max(10, (width-295)//8)], muted)
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
        text(10, 60, 'ESTIMATED CAST TIMERS — ANNOUNCEMENTS DO NOT CONFIRM HEALS', '#627e85', ('Consolas', 8))

    def draw_tick(self,x,y,width,now):
        from layout_tools import tick_snapshot
        data=tick_snapshot(self.misc,now);cv=self.canvas
        cv.create_rectangle(x,y,x+width,y+21,fill='#061014',outline='#9d8545')
        label='~TICK '+format(data['remaining'],'.1f')+'s' if data['synced'] else 'TICK: SYNC IN SETTINGS'
        cv.create_text(x+6,y+2,text=label,fill='#d4b363',anchor='nw',font=('Consolas',9,'bold'))
        cv.create_rectangle(x+3,y+18,x+3+(width-6)*data['fraction'],y+20,fill='#3db8a7',outline='')

    def save_timer_panel(self,**changes):
        settings=settings_store.load();settings['timers'].update(changes);settings_store.save(settings);self.timers.configure(settings['timers'])

    def save_timer_position(self,x,y):
        settings=settings_store.load();settings['timers'].update(x=int(x),y=int(y),move_mode=False);settings_store.save(settings);self.timers.configure(settings['timers'])

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
                    shared_settings=settings_store.load()
                    self.triggers.configure(shared_settings['triggers'])
                    self.timers.configure(shared_settings['timers'])
                    self.misc=shared_settings['misc']
                    self.buffs.configure(shared_settings['buffs'])
                    if prefs != self.chain.config:
                        self.chain = Chain(prefs); self.beep_key = None
                    if self.follower.refresh():
                        name, server = identity(self.follower.path); self.character = name+' ['+server+']'
                        self.xp_replayed_to=self.experience.set_character(self.follower.path,now)
                        self.triggers.set_character(self.follower.path)
                        self.timers.set_character(name,server)
                        self.maps.set_character(name,self.follower.path)
                        # Restore zone context only; historical lines never start timers.
                        try:
                            with self.follower.path.open('rb') as log:
                                log.seek(max(0,self.follower.path.stat().st_size-1048576));tail=log.read().decode('utf-8',errors='replace')
                            for historical in tail.splitlines():
                                if any(marker in historical for marker in ['You have entered ','LOADING, PLEASE WAIT','Welcome to EverQuest!']):self.maps.consume(historical,now)
                        except OSError:pass
                        self.buffs.set_character(name,self.follower.path)
                        self.buff_replayed_to = self.buffs.log_offset or 0
                        self.chain = Chain(self.chain.config); self.beep_key = None
                    if game: self.seen_game = True; self.gone_since = None
                    elif self.seen_game and self.gone_since is None: self.gone_since = mono
                    elif self.gone_since and mono-self.gone_since > 15 and not os.environ.get('BFT_MANAGED_SESSION'):
                        self.root.destroy(); return
                for line in self.follower.read_lines():
                    if self.follower.stream.tell()>self.xp_replayed_to:self.experience.consume(line,now,self.follower.stream.tell())
                    if self.follower.stream.tell()>self.buff_replayed_to:
                        self.triggers.consume(line,now)
                        self.maps.consume(line,now)
                        self.timers.consume(line,now,self.maps.zone)
                    self.chain.consume(line, now, self.character.split(' [')[0])
                    if self.follower.stream.tell()>self.buff_replayed_to:self.buffs.consume(line,now)
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
                        if self.misc['tick_enabled']:self.draw_tick(max(0,strip_width-182),53,176,now)
                    elif self.misc['tick_enabled']:
                        tick_width=min(180,max(1,width-16));tick_x=max(0,width-tick_width-8)
                        self.root.geometry(f'{tick_width}x23');self.root.deiconify();self.root.update_idletasks()
                        handle=self.win.clickthrough(self.root)
                        self.win.u.SetWindowPos(handle,ctypes.c_void_p(-1),x+tick_x,y+oy,tick_width,23,0x0010)
                        self.canvas.delete('all');self.draw_tick(0,0,tick_width-1,now)
                    else: self.root.withdraw()
                else: self.root.withdraw()
            if not self.args.demo:
                self.timers.tick(now)
                self.timer_overlay.update(game,self.timers,now)
                self.trigger_overlay.update(game,self.triggers,now)
                context=(self.triggers.profile_key,self.triggers.current_class(),self.triggers.zone)
                if getattr(self,'speech_context',context)!=context:self.speech.cancel()
                self.speech_context=context
                self.speech.configure(self.triggers.config)
                audio=self.triggers.take_audio()
                timer_audio=self.timers.take_audio()
                if self.triggers.config['sound_enabled']:audio+=timer_audio
                if self.triggers.config['audio_mode']=='speech':
                    for alert in audio:self.speech.speak(alert['text'],self.triggers.config,alert['severity'])
                elif audio:
                    import winsound
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                self.buff_overlay.update(game,self.buffs,now)
                if mono-self.last_buff_status>=2:
                    self.last_buff_status=mono
                    try:
                        RUNTIME.mkdir(parents=True,exist_ok=True)
                        self.experience.heartbeat(now,max(self.xp_replayed_to,self.follower.stream.tell()) if self.follower.stream else None)
                        self.buffs.save_state(now,log_offset=max(self.buff_replayed_to,self.follower.stream.tell()) if self.follower.stream else None)
                        (RUNTIME/'buff-status.json').write_text(json.dumps(self.buffs.snapshot(now)),encoding='utf-8')
                    except OSError:pass
            control = bool(self.win.u.GetAsyncKeyState(0x11) & 0x8000)
            down = control and bool((self.win.u.GetAsyncKeyState(ord('J')) | self.win.u.GetAsyncKeyState(ord('H'))) & 0x8000)
            if down and not self.key_was_down and (self.args.demo or (game and self.win.u.GetForegroundWindow() == game[0])): self.edit()
            self.key_was_down = down
            self.last_error = ''
        except (OSError, ValueError, sqlite3.Error) as e:
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
            app.buffs.save_state(log_offset=max(app.buff_replayed_to,app.follower.stream.tell()) if app.follower.stream else None)
            app.experience.heartbeat();app.experience.close()
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
