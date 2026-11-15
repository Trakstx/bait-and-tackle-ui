"""One authenticated loopback HTML settings page. No game commands or memory access."""
import json
import sqlite3
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from chchain import Chain
import settings_store
import time
import os
import subprocess

class Hub:
    def __init__(self, path=settings_store.PATH, game=None):
        self.path=Path(path);self.token=secrets.token_urlsafe(32);self.lock=threading.Lock()
        from updates import Updates
        self.updates=Updates()
        hub=self
        self.encounter = None
        self.buff_engine = None
        self.trigger_engine = None
        self.timers = None
        from recorder import Recorder
        self.recorder=Recorder(settings_store.load(self.path)['recorder'],game=game)
        from speech_alerts import Speech
        self.speech = Speech()
        self.experience = None
        from eq_maps import MapCatalog
        self.map_catalog = MapCatalog()
        self.map_tracker = None
        from layout_tools import LayoutService
        self.layouts = LayoutService(game,settings_store.RUNTIME/'layouts')
        from vision_fix import VisionFix
        self.vision=VisionFix(game,settings_store.RUNTIME)
        from item_icons import ItemIcons
        self.icons = ItemIcons(settings_store.RUNTIME/'item-icons')
        self.game = Path(game) if game is not None else None
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def reply(self,status,data,kind='application/json'):
                if not isinstance(data,bytes):data=json.dumps(data).encode('utf-8')
                self.send_response(status);self.send_header('Content-Type',kind+'; charset=utf-8')
                self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
                self.send_header('X-Frame-Options','DENY')
                self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'")
                self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
            def auth(self):
                return self.headers.get('Host')==hub.host and secrets.compare_digest(self.headers.get('X-BFT-Token',''),hub.token)
            def do_GET(self):
                url=urlsplit(self.path)
                if self.headers.get('Host')!=hub.host:return self.reply(403,{'error':'Wrong host'})
                if url.path=='/' and secrets.compare_digest(parse_qs(url.query).get('key',[''])[0],hub.token):
                    return self.reply(200,(Path(__file__).with_name('settings.html')).read_bytes(),'text/html')
                if url.path in ['/settings.js','/settings.css','/maps.js','/misc.js','/experience.js','/triggers.js','/timers.js','/recorder.js','/updates.js','/klandicar.js']:
                    return self.reply(200,Path(__file__).with_name(url.path[1:]).read_bytes(),'text/javascript' if url.path.endswith('.js') else 'text/css')
                if url.path=='/api/item-icon' and secrets.compare_digest(parse_qs(url.query).get('key',[''])[0],hub.token):
                    args=parse_qs(url.query)
                    try:
                        image=hub.icons.get(args.get('id',['0'])[0],args.get('name',[''])[0])
                        return self.reply(200,image,'image/png')
                    except Exception:
                        return self.reply(404,{'error':'Item artwork unavailable'})
                if url.path=='/api/spell-icon' and secrets.compare_digest(parse_qs(url.query).get('key',[''])[0],hub.token):
                    try:
                        from spell_icons import SpellIcons
                        if not hasattr(hub,'spell_icons'):hub.spell_icons=SpellIcons(hub.game)
                        return self.reply(200,hub.spell_icons.get(parse_qs(url.query).get('id',['0'])[0]),'image/png')
                    except (OSError,ValueError,TypeError):return self.reply(404,{'error':'Spell icon unavailable'})
                if url.path=='/api/maps/catalog' and self.auth():
                    return self.reply(200,hub.map_catalog.catalog())
                if url.path=='/api/maps/state' and self.auth():
                    return self.reply(200,hub.map_tracker.snapshot(time.time()) if hub.map_tracker else {'character':'Waiting for next launcher session','zone':None,'position':None,'age':None})
                if url.path=='/api/maps/image' and secrets.compare_digest(parse_qs(url.query).get('key',[''])[0],hub.token):
                    try:
                        data,kind=hub.map_catalog.image(parse_qs(url.query).get('id',[''])[0])
                        return self.reply(200,data,kind)
                    except (ValueError,OSError):return self.reply(404,{'error':'Map not found'})
                if url.path=='/api/maps/license' and secrets.compare_digest(parse_qs(url.query).get('key',[''])[0],hub.token):
                    return self.reply(200,(hub.map_catalog.root/'LICENSE-ZlizEQMap.txt').read_bytes(),'text/plain')
                if url.path=='/api/buff-catalog' and self.auth():
                    from buff_timers import spell_catalog
                    spells=spell_catalog(hub.game/'spells_us.txt') if hub.game else {}
                    return self.reply(200,{'spells':list(spells)})
                if url.path=='/api/buffs' and self.auth():
                    return self.reply(200,hub.buff_engine.snapshot(time.time()) if hub.buff_engine else {'note':'Buff reader starts with the next launcher session.','timers':[]})
                if url.path=='/api/bank' and self.auth():
                    from dashboard_data import bank_snapshot
                    return self.reply(200,bank_snapshot(hub.game))
                if url.path=='/api/history' and self.auth():
                    from dashboard_data import history_snapshot
                    character=parse_qs(url.query).get('character',[''])[0]
                    return self.reply(200,history_snapshot(settings_store.RUNTIME/'history',character))
                if url.path=='/api/klandicar' and self.auth():return self.reply(200,{'settings':settings_store.load(hub.path)['klandicar'],'encounter':hub.encounter.snapshot(time.time()) if hub.encounter else None})
                if url.path=='/api/updates' and self.auth():return self.reply(200,hub.updates.snapshot())
                if url.path=='/api/recorder' and self.auth():return self.reply(200,hub.recorder.snapshot())
                if url.path=='/api/aggro' and self.auth():
                    try:status=json.loads((settings_store.RUNTIME/'threat-status.json').read_text())
                    except (OSError,ValueError):status={'notes':'Waiting for the refreshed combat reader.'}
                    return self.reply(200,status)
                if url.path=='/api/timers' and self.auth():return self.reply(200,hub.timers.snapshot(time.time()) if hub.timers else {'alerts':[],'error':'Refresh the helper to start timers.'})
                if url.path=='/api/triggers/audio' and self.auth():return self.reply(200,hub.speech.snapshot())
                if url.path=='/api/triggers' and self.auth():
                    from class_triggers import TriggerEngine
                    engine=hub.trigger_engine or TriggerEngine(settings_store.load(hub.path)['triggers'])
                    return self.reply(200,engine.snapshot(time.time()))
                if url.path=='/api/experience' and self.auth():
                    args=parse_qs(url.query)
                    return self.reply(200,hub.experience.snapshot(args.get('character',[''])[0],args.get('session',[''])[0],kind=args.get('kind',['all'])[0],page=int(args.get('page',['0'])[0]) if args.get('page',['0'])[0].isdigit() else 0) if hub.experience else {'characters':[],'sessions':[],'session':None,'events':[],'active':None,'note':'Experience tracking starts with the next Bait & Tackle session.'})
                if url.path=='/api/vision' and self.auth():return self.reply(200,hub.vision.status())
                if url.path=='/api/layouts' and self.auth():
                    return self.reply(200,hub.layouts.snapshot())
                if url.path=='/api/settings' and self.auth():
                    return self.reply(200,settings_store.load(hub.path))
                return self.reply(403,{'error':'Open settings through Ctrl+J.'})
            def do_POST(self):
                if not self.auth() or self.headers.get('Origin') != 'http://'+hub.host:return self.reply(403,{'error':'Unauthorized request'})
                try:
                    if self.path in ['/api/updates/check','/api/updates/download']:return self.reply(200,hub.updates.request(self.path.rsplit('/',1)[1]))
                    length=int(self.headers.get('Content-Length','0'))
                    if not 0<length<=65536:return self.reply(413,{'error':'Request too large'})
                    data=json.loads(self.rfile.read(length))
                    with hub.lock:
                        if self.path=='/api/klandicar/config':
                            value=settings_store.load(hub.path);value['klandicar']=data;value=settings_store.save(value,hub.path)
                            if hub.encounter:hub.encounter.configure(value['klandicar'])
                            return self.reply(200,value['klandicar'])
                        if self.path in ('/api/klandicar/arm','/api/klandicar/stop'):
                            if not hub.encounter:raise ValueError('Refresh the Bait & Tackle helper to load the encounter strip.')
                            if self.path.endswith('/arm'):hub.encounter.arm()
                            else:hub.encounter.disarm()
                            return self.reply(200,hub.encounter.snapshot(time.time()))
                        if self.path=='/api/recorder/config':
                            value=settings_store.load(hub.path);hub.recorder.configure(data);value['recorder']=hub.recorder.config;value=settings_store.save(value,hub.path)
                            return self.reply(200,value['recorder'])
                        if self.path in ('/api/recorder/start','/api/recorder/stop','/api/recorder/save'):
                            action=self.path.rsplit('/',1)[1]
                            if action in ('start','stop'):
                                value=settings_store.load(hub.path);value['recorder']['enabled']=action=='start';value=settings_store.save(value,hub.path);hub.recorder.configure(value['recorder'])
                            hub.recorder.action(action)
                            return self.reply(200,{'queued':True})
                        if self.path=='/api/aggro/config':
                            value=settings_store.load(hub.path);value['aggro']=data;value=settings_store.save(value,hub.path)
                            return self.reply(200,value['aggro'])
                        if self.path=='/api/timers/panel':
                            if not data or any(k not in ('visible','collapsed') or not isinstance(v,bool) for k,v in data.items()):raise ValueError('Invalid panel controls.')
                            value=settings_store.load(hub.path);value['timers'].update(data);value=settings_store.save(value,hub.path)
                            if hub.timers:hub.timers.configure(value['timers'])
                            return self.reply(200,value['timers'])
                        if self.path=='/api/timers/config':
                            value=settings_store.load(hub.path);value['timers']=data;value=settings_store.save(value,hub.path)
                            if hub.timers:hub.timers.configure(value['timers'])
                            return self.reply(200,value['timers'])
                        if self.path in ('/api/timers/start','/api/timers/remove','/api/timers/refresh'):
                            if not hub.timers:raise ValueError('Refresh the helper to start timers.')
                            if self.path.endswith('/start'):hub.timers.start(data.get('name','Custom timer'),data['duration'])
                            elif self.path.endswith('/remove'):hub.timers.remove(data['id'])
                            else:
                                if time.time()+85<hub.timers.next_fetch:raise ValueError('Please wait a few seconds before refreshing again.')
                                hub.timers.next_fetch=0
                            return self.reply(200,{'saved':True})
                        if self.path=='/api/triggers/config':
                            value=settings_store.load(hub.path);value['triggers']=data;value=settings_store.save(value,hub.path)
                            if hub.trigger_engine:hub.trigger_engine.configure(value['triggers'])
                            return self.reply(200,value['triggers'])
                        if self.path=='/api/triggers/audio/test':
                            from class_triggers import validate
                            prefs=validate(data.get('config',{}))
                            hub.speech.speak('Bait and Tackle spoken alerts are ready.',prefs)
                            return self.reply(200,{'queued':True})
                        if self.path=='/api/triggers/test':
                            from class_triggers import TriggerEngine
                            engine=hub.trigger_engine or TriggerEngine(settings_store.load(hub.path)['triggers'])
                            result=engine.test(data)
                            if data.get('speak') and result['matched']:
                                from class_triggers import validate
                                hub.speech.speak(result['message'],validate(data.get('config',{})))
                            return self.reply(200,result)
                        if self.path.startswith('/api/experience/'):
                            if hub.experience is None:raise ValueError('Restart Bait & Tackle to start experience tracking.')
                            level=data.get('level');percent=data.get('percent')
                            if self.path=='/api/experience/start':hub.experience.start_manual(data.get('name','Timed session'),level=level,percent=percent)
                            elif self.path=='/api/experience/stop':hub.experience.stop_manual(level=level,percent=percent)
                            elif self.path=='/api/experience/checkpoint':hub.experience.checkpoint(level,percent)
                            else:return self.reply(404,{'error':'Not found'})
                            return self.reply(200,{'saved':True})
                        if self.path=='/api/vision':return self.reply(200,hub.vision.queue(str(data['mode'])))
                        if self.path=='/api/layouts/preview':return self.reply(200,hub.layouts.preview(data))
                        if self.path=='/api/layouts/queue':return self.reply(200,hub.layouts.queue(data))
                        if self.path=='/api/layouts/cancel':return self.reply(200,hub.layouts.cancel(str(data['id'])))
                        if self.path=='/api/misc/tick-sync':
                            value=settings_store.load(hub.path);value['misc']['tick_anchor']=time.time();value['misc']['tick_enabled']=True
                            return self.reply(200,settings_store.save(value,hub.path)['misc'])
                        if self.path=='/api/settings':return self.reply(200,settings_store.save(data,hub.path))
                        if self.path=='/api/buffs/dismiss' and getattr(hub,'buff_engine',None):
                            hub.buff_engine.dismiss(str(data['name']))
                            return self.reply(200,{'dismissed':True})
                        if self.path=='/api/test':
                            chain=Chain(data['ch']);ok=chain.consume(str(data.get('sample','')),time.time(),'You')
                            return self.reply(200,{'matched':ok,'slot':chain.last.slot if ok else '', 'target':chain.last.target if ok else ''})
                    self.reply(404,{'error':'Not found'})
                except (ValueError,TypeError,KeyError,AttributeError,OSError,sqlite3.Error) as e:self.reply(400,{'error':str(e)})
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.host='127.0.0.1:'+str(self.server.server_port)
        if os.environ.get('BFT_MANAGED_SESSION'):
            from runtime_paths import install_state
            (install_state(Path(__file__).parent)/'dashboard-session.json').write_text(json.dumps({'url':self.url,'pid':os.getpid()}),encoding='utf-8')
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    @property
    def url(self):return 'http://'+self.host+'/?key='+self.token
    def open(self):
        if os.name=='nt':
            import ctypes
            from ctypes import wintypes
            user=ctypes.WinDLL('user32',use_last_error=True)
            user.FindWindowW.argtypes=[wintypes.LPCWSTR,wintypes.LPCWSTR];user.FindWindowW.restype=wintypes.HWND
            user.SetForegroundWindow.argtypes=[wintypes.HWND];user.ShowWindow.argtypes=[wintypes.HWND,ctypes.c_int]
            window=user.FindWindowW(None,'Bait & Tackle - Dashboard')
            if window and getattr(self,'opened',False):
                user.ShowWindow(window,9);user.SetForegroundWindow(window);return
            if window:
                user.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,ctypes.c_size_t,ctypes.c_ssize_t]
                user.PostMessageW(window,0x10,0,0)
            if time.monotonic()-getattr(self,'last_open',0)<3:return
            self.last_open=time.monotonic()
            for variable in ['PROGRAMFILES(X86)','PROGRAMFILES','LOCALAPPDATA']:
                edge=Path(os.environ.get(variable,''))/'Microsoft/Edge/Application/msedge.exe'
                if edge.is_file():
                    subprocess.Popen([str(edge),'--app='+self.url,'--user-data-dir='+str(settings_store.RUNTIME/('settings-browser-'+str(os.getpid()))),'--no-first-run'],creationflags=subprocess.CREATE_NO_WINDOW)
                    self.opened=True
                    return
        webbrowser.open(self.url,new=0,autoraise=True)
    def close(self):
        self.recorder.close()
        if self.timers:self.timers.close()
        self.speech.close()
        if os.name=='nt' and getattr(self,'opened',False):
            import ctypes
            from ctypes import wintypes
            user=ctypes.WinDLL('user32',use_last_error=True)
            user.FindWindowW.argtypes=[wintypes.LPCWSTR,wintypes.LPCWSTR];user.FindWindowW.restype=wintypes.HWND
            user.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,ctypes.c_size_t,ctypes.c_ssize_t]
            window=user.FindWindowW(None,'Bait & Tackle - Dashboard')
            if window:user.PostMessageW(window,0x10,0,0)
        self.server.shutdown();self.server.server_close()
