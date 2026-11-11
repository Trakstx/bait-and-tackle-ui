"""One authenticated loopback HTML settings page. No game commands or memory access."""
import json
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
    def __init__(self, path=settings_store.PATH):
        self.path=Path(path);self.token=secrets.token_urlsafe(32);self.lock=threading.Lock()
        hub=self
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
                if url.path in ['/settings.js','/settings.css']:
                    return self.reply(200,Path(__file__).with_name(url.path[1:]).read_bytes(),'text/javascript' if url.path.endswith('.js') else 'text/css')
                if url.path=='/api/settings' and self.auth():
                    return self.reply(200,settings_store.load(hub.path))
                return self.reply(403,{'error':'Open settings through Ctrl+J.'})
            def do_POST(self):
                if not self.auth() or self.headers.get('Origin') != 'http://'+hub.host:return self.reply(403,{'error':'Unauthorized request'})
                try:
                    length=int(self.headers.get('Content-Length','0'))
                    if not 0<length<=65536:return self.reply(413,{'error':'Request too large'})
                    data=json.loads(self.rfile.read(length))
                    with hub.lock:
                        if self.path=='/api/settings':return self.reply(200,settings_store.save(data,hub.path))
                        if self.path=='/api/test':
                            chain=Chain(data['ch']);ok=chain.consume(str(data.get('sample','')),time.time(),'You')
                            return self.reply(200,{'matched':ok,'slot':chain.last.slot if ok else '', 'target':chain.last.target if ok else ''})
                    self.reply(404,{'error':'Not found'})
                except (ValueError,TypeError,KeyError,AttributeError,OSError) as e:self.reply(400,{'error':str(e)})
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.host='127.0.0.1:'+str(self.server.server_port)
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
            window=user.FindWindowW(None,'Bait & Tackle — Settings')
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
                    subprocess.Popen([str(edge),'--app='+self.url,'--user-data-dir='+str(settings_store.RUNTIME/'settings-browser'),'--no-first-run'],creationflags=subprocess.CREATE_NO_WINDOW)
                    self.opened=True
                    return
        webbrowser.open(self.url,new=0,autoraise=True)
    def close(self):
        if os.name=='nt' and getattr(self,'opened',False):
            import ctypes
            from ctypes import wintypes
            user=ctypes.WinDLL('user32',use_last_error=True)
            user.FindWindowW.argtypes=[wintypes.LPCWSTR,wintypes.LPCWSTR];user.FindWindowW.restype=wintypes.HWND
            user.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,ctypes.c_size_t,ctypes.c_ssize_t]
            window=user.FindWindowW(None,'Bait & Tackle — Settings')
            if window:user.PostMessageW(window,0x10,0,0)
        self.server.shutdown();self.server.server_close()
