"""Name-checked public item artwork, cached locally; no game access."""
import html
import json
import re
import threading
import time
import struct
import urllib.request
from pathlib import Path

class ItemIcons:
    def __init__(self, directory):
        self.directory=Path(directory);self.guard=threading.Lock();self.locks={};self.failures={}
    def get(self, item_id, name):
        identity=(int(item_id),name)
        if self.failures.get(identity,0)>time.monotonic():raise ValueError("Artwork unavailable; retry later")
        try:return self._get(item_id,name)
        except Exception:
            self.failures[identity]=time.monotonic()+300
            raise
    def _get(self, item_id, name):
        item_id=int(item_id)
        if not 0<item_id<10000000 or not name or len(name)>200:raise ValueError('Invalid item')
        with self.guard:lock=self.locks.setdefault(item_id,threading.Lock())
        with lock:
            png=self.directory/(str(item_id)+'.png');meta=self.directory/(str(item_id)+'.json')
            normal=lambda s:' '.join(html.unescape(s).casefold().split())
            try:
                data=json.loads(meta.read_text(encoding='utf-8'))
                if normal(data['name'])==normal(name) and png.is_file():return png.read_bytes()
            except (OSError,ValueError,KeyError,TypeError):pass
            def fetch(url,limit):
                request=urllib.request.Request(url,headers={'User-Agent':'BaitAndTackle/0.7 (user-requested item artwork)'})
                with urllib.request.urlopen(request,timeout=12) as response:
                    if response.geturl().split('/')[2] not in ('lucy.allakhazam.com','everquest.allakhazam.com'):raise ValueError('Unexpected artwork redirect')
                    body=response.read(limit+1)
                if len(body)>limit:raise ValueError('Artwork response too large')
                return body
            page=fetch('https://lucy.allakhazam.com/item.html?id='+str(item_id),2000000).decode('utf-8',errors='replace')
            # Item IDs can differ between servers; never silently assign a mismatched icon.
            title=re.search(r'Item Details for\s+(.+?)\s+:: Lucy',page)
            if not title or normal(title[1])!=normal(name):raise ValueError('Item ID/name mismatch')
            icon=re.search(r'https://everquest\.allakhazam\.com/pgfx/item_(\d+)\.png',page)
            if not icon:raise ValueError('No item artwork')
            image=fetch(icon[0],262144)
            if not image.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('Invalid item image')
            if len(image)<24 or max(struct.unpack('>II',image[16:24]))>512:raise ValueError('Invalid icon dimensions')
            self.directory.mkdir(parents=True,exist_ok=True)
            png.write_bytes(image)
            meta.write_text(json.dumps({'name':name,'icon':int(icon[1]),'source':icon[0]}),encoding='utf-8')
            return image
