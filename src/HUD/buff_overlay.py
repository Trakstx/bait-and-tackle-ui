"""Classic buff-slot column, independent stable slots, from log-observed buffs."""
import base64
import ctypes
from pathlib import Path
import tkinter as tk
from spell_icons import SpellIcons,tga_rgba,png_rgba

class BuffOverlay:
    def __init__(self,parent,win,game):
        self.win=win;self.game=Path(game);self.icons=SpellIcons(game);self.images={};self.frame=None
        self.root=tk.Toplevel(parent);self.root.title('BFT Buff Timers');self.root.withdraw();self.root.overrideredirect(True)
        self.root.configure(bg='#010203');self.root.attributes('-topmost',True);self.root.attributes('-transparentcolor','#010203')
        self.canvas=tk.Canvas(self.root,bg='#010203',highlightthickness=0);self.canvas.pack(fill='both',expand=True)
        # Exact 24x24 Buff_BackgroundSingle texture from the installed skin.
        for directory in ['BAIT_AND_FUCKING_TACLE','default']:
            try:
                path=self.game/'uifiles'/directory/'Buff_Background.tga'
                width,height,pixels=tga_rgba(path.read_bytes())
                crop=b''.join(pixels[((1+y)*width+1)*4:((1+y)*width+25)*4] for y in range(24))
                self.frame=tk.PhotoImage(data=base64.b64encode(png_rgba(24,24,crop)));break
            except (OSError,ValueError,tk.TclError):continue
    def image(self,index):
        if index not in self.images:
            try:self.images[index]=tk.PhotoImage(data=base64.b64encode(self.icons.get(index))).subsample(2,2)
            except (OSError,ValueError,tk.TclError):self.images[index]=None
        return self.images[index]
    def update(self,game,engine,now):
        prefs=engine.config;timers=engine.snapshot(now)['timers']
        if not game or not prefs['enabled'] or self.win.u.GetForegroundWindow()!=game[0]:self.root.withdraw();return
        _,x,y,width,height=game
        w=min(prefs['width'],max(1,width));left=min(max(0,prefs['x']),max(0,width-w));top=min(max(0,prefs['y']),max(0,height-24))
        spacing=prefs['row_height'];h=min(14*spacing+25,max(1,height-top));icon_x=w-24
        self.root.geometry(f'{w}x{h}');self.root.deiconify();self.root.update_idletasks();handle=self.win.clickthrough(self.root)
        # Background is transparent. Only slots, icons and labels are drawn.
        if hasattr(self.win.u,'SetLayeredWindowAttributes'):self.win.u.SetLayeredWindowAttributes(handle,0x030201,255,3)
        self.win.u.SetWindowPos(handle,ctypes.c_void_p(-1),x+left,y+top,w,h,0x0010)
        cv=self.canvas;cv.delete('all');slots={row['display_slot']:row for row in timers if row.get('display_slot')}
        for number in range(1,16):
            y=1+(number-1)*spacing
            if self.frame:cv.create_image(icon_x,y,image=self.frame,anchor='nw')
            else:cv.create_rectangle(icon_x,y,w-1,y+23,outline='#777563',fill='#070b0b')
            timer=slots.get(number)
            if timer is None:
                cv.create_text(icon_x+12,y+12,text=str(number),font=('Arial',8),fill='#afafaf')
                continue
            image=self.image(timer['icon'])
            if image:cv.create_image(icon_x+2,y+2,image=image,anchor='nw')
            else:cv.create_text(icon_x+12,y+12,text='?',fill='#ded2a4')
            remaining=timer['remaining'];minimum=timer['minimum_remaining']
            def stamp(seconds):return f'{seconds//60}:{seconds%60:02}'
            text='unknown' if remaining is None else '~'+(stamp(minimum)+'-'+stamp(remaining) if minimum!=remaining else stamp(remaining))
            color='#ffb08e' if remaining is not None and remaining<=30 else '#ddd2a2'
            # Native-style name beside the icon; compact estimate underneath.
            label_width=max(1,icon_x-8)
            name=('?' if timer.get('identity')=='inferred' or timer.get('uncertain') else '')+timer['name'];max_chars=max(4,int(label_width/6))
            if len(name)>max_chars:name=name[:max_chars-1]+'…'
            cv.create_text(icon_x-5,y+2,text=name,anchor='ne',font=('Arial',8),fill='#efefef')
            cv.create_text(icon_x-5,y+13,text=text,anchor='ne',font=('Consolas',8,'bold'),fill=color)
        if not timers:cv.create_text(icon_x-5,7,text='Awaiting buff landing',anchor='ne',font=('Arial',8),fill='#afafaf')
