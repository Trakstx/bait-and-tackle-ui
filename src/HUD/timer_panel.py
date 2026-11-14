"""Retractable timer panel: interactive header, separate click-through countdown body."""
import ctypes,math,tkinter as tk

def clock(seconds):
 value=max(0,math.ceil(seconds));hours,value=divmod(value,3600);minutes,seconds=divmod(value,60)
 return f'{hours}:{minutes:02}:{seconds:02}' if hours else f'{minutes}:{seconds:02}'

class TimerPanel:
 def __init__(self,parent,win,save_position,save_panel):
  self.win=win;self.save_position=save_position;self.save_panel=save_panel;self.engine=None;self.game=None;self.drag=None;self.handle=None;self.body_handle=None;self.signature=None;self.resizing=None;self.resize_size=None;self.grip_handle=None
  self.root=tk.Toplevel(parent);self.root.title('BFT Timers');self.root.withdraw();self.root.overrideredirect(True);self.root.attributes('-topmost',True)
  self.header=tk.Canvas(self.root,bg='#071114',highlightthickness=1,highlightbackground='#b99b52');self.header.pack(fill='both',expand=True)
  self.body=tk.Toplevel(parent);self.body.title('BFT Timer Countdowns');self.body.withdraw();self.body.overrideredirect(True);self.body.attributes('-topmost',True)
  self.canvas=tk.Canvas(self.body,bg='#071114',highlightthickness=1,highlightbackground='#b99b52');self.canvas.pack(fill='both',expand=True)
  self.grip=tk.Toplevel(parent);self.grip.title('BFT Timer Resize');self.grip.withdraw();self.grip.overrideredirect(True);self.grip.attributes('-topmost',True)
  grip=tk.Canvas(self.grip,width=16,height=16,bg='#183038',highlightthickness=0,cursor='size_nw_se');grip.pack(fill='both',expand=True)
  for offset in [4,8,12]:grip.create_line(offset,15,15,offset,fill='#d4b363')
  grip.bind('<ButtonPress-1>',self.resize_begin);grip.bind('<B1-Motion>',self.resize_motion);grip.bind('<ButtonRelease-1>',self.resize_end)
  self.header.bind('<ButtonPress-1>',self.press);self.header.bind('<B1-Motion>',self.motion);self.header.bind('<ButtonRelease-1>',self.release)
 def resize_begin(self,event):
  if self.engine and not self.engine.config['collapsed']:
   self.resizing=(event.x_root,event.y_root,self.root.winfo_width(),self.body.winfo_height()+28);self.resize_size=self.resizing[2:]
 def resize_motion(self,event):
  if not self.resizing or not self.game:return
  sx,sy,w,h=self.resizing;_,gx,gy,gw,gh=self.game;maxw=max(240,min(800,gx+gw-self.root.winfo_x()));maxh=max(92,min(800,gy+gh-self.root.winfo_y()))
  self.resize_size=(min(maxw,max(240,w+event.x_root-sx)),min(maxh,max(92,h+event.y_root-sy)));self.update(self.game,self.engine,self.last_now)
 def resize_end(self,event):
  if self.resizing:
   width,height=self.resize_size;self.resizing=None;self.resize_size=None;self.save_panel(width=int(width),height=int(height));self.signature=None
 def press(self,event):
  if not self.engine:return
  width=self.root.winfo_width()
  if event.x>=width-28:self.save_panel(visible=False);return
  if event.x>=width-58:self.save_panel(collapsed=not self.engine.config['collapsed']);return
  self.drag=(event.x_root-self.root.winfo_x(),event.y_root-self.root.winfo_y())
 def motion(self,event):
  if not self.drag or not self.game:return
  _,gx,gy,gw,gh=self.game;oldx,oldy=self.root.winfo_x(),self.root.winfo_y();x=min(max(gx,event.x_root-self.drag[0]),gx+max(0,gw-self.root.winfo_width()));y=min(max(gy,event.y_root-self.drag[1]),gy+max(0,gh-28))
  self.root.geometry(f'+{x}+{y}');self.body.geometry(f'+{self.body.winfo_x()+x-oldx}+{self.body.winfo_y()+y-oldy}');self.grip.geometry(f'+{self.grip.winfo_x()+x-oldx}+{self.grip.winfo_y()+y-oldy}')
 def release(self,event):
  if self.drag and self.game:
   self.drag=None;_,gx,gy,_,_=self.game;self.save_position(max(0,self.root.winfo_x()-gx),max(0,self.root.winfo_y()-gy))
 def hide(self):self.root.withdraw();self.body.withdraw();self.grip.withdraw()
 def update(self,game,engine,now):
  self.last_now=now;self.game=game;self.engine=engine;p=engine.config;snap=engine.snapshot(now);rows=snap['alerts'][:p['rows']]
  if not game or not p['enabled'] or not p['visible'] or self.win.u.GetForegroundWindow() not in [game[0],self.handle,self.grip_handle]:self.hide();return
  if self.drag:return
  _,gx,gy,gw,gh=game;w=min(240 if p['collapsed'] else p['width'],gw);h=min(p.get('height',0) or (44+max(1,len(rows))*48),gh)
  if self.resize_size and not p['collapsed']:w,h=self.resize_size
  x=min(p['x'],max(0,gw-w));y=min(p['y'],max(0,gh-(28 if p['collapsed'] else h)))
  rows=rows[:max(1,(h-44)//48)]
  self.root.geometry(f'{w}x28');self.root.deiconify();self.root.update_idletasks();self.handle=self.win.clickthrough(self.root)
  # Keep NOACTIVATE, remove only click-through on the compact header controls.
  self.win.set_style(self.handle,-20,self.win.get_style(self.handle,-20)&~0x20)
  self.win.u.SetWindowPos(self.handle,ctypes.c_void_p(-1),gx+x,gy+y,w,28,0x0010)
  cv=self.header;cv.delete('all');cv.create_text(9,7,text=f'TIMERS ({len(snap["alerts"])})',anchor='nw',font=('Consolas',10,'bold'),fill='#d4b363')
  for left,label in [(w-57,'+' if p['collapsed'] else '-'),(w-27,'X')]:
   cv.create_rectangle(left,3,left+24,24,fill='#183038',outline='#897746');cv.create_text(left+12,13,text=label,fill='#f3dfab',font=('Arial',11,'bold'))
  if p['collapsed']:self.body.withdraw();self.grip.withdraw();return
  bh=max(1,h-28);self.body.geometry(f'{w}x{bh}');self.body.deiconify();self.body.update_idletasks();self.body_handle=self.win.clickthrough(self.body);self.win.u.SetWindowPos(self.body_handle,ctypes.c_void_p(-1),gx+x,gy+y+28,w,bh,0x0010)
  self.grip.geometry('16x16');self.grip.deiconify();self.grip.update_idletasks();self.grip_handle=self.win.clickthrough(self.grip);self.win.set_style(self.grip_handle,-20,self.win.get_style(self.grip_handle,-20)&~0x20);self.win.u.SetWindowPos(self.grip_handle,ctypes.c_void_p(-1),gx+x+w-16,gy+y+h-16,16,16,0x0010)
  cv=self.canvas;signature=(w,bh,tuple((r['id'],math.ceil(r['remaining']),r['status'],r['detail']) for r in rows))
  if signature==self.signature:return
  self.signature=signature;cv.delete('all')
  if not rows:cv.create_text(10,16,text='No active timers',anchor='nw',fill='#a1babb',font=('Arial',10))
  for i,row in enumerate(rows):
   top=i*48;color='#ffd080' if row['severity']=='warn' else '#91c9c1';stamp=clock(row['remaining']) if row['status']=='Running' else row['status'];limit=max(8,(w-140)//8)
   cv.create_text(9,top+6,text=row['name'][:limit],anchor='nw',fill='#edf1e8',font=('Consolas',10,'bold'));cv.create_text(w-9,top+6,text=stamp,anchor='ne',fill=color,font=('Consolas',11,'bold'))
   cv.create_text(9,top+25,text=row['detail'][:max(12,(w-20)//6)],anchor='nw',fill='#a1babb',font=('Arial',8))
   cv.create_rectangle(6,top+45,6+(w-12)*min(1,row['remaining']/max(1,row['duration'])),top+47,fill=color,outline='')
