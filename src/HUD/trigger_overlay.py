"""Movable Bait & Tackle alert panel; clicks pass through outside placement mode."""

import ctypes,tkinter as tk

class TriggerOverlay:

 def __init__(self,parent,win,save_position):

  self.win=win;self.save_position=save_position;self.engine=None;self.game=None;self.drag=None;self.handle=None

  self.root=tk.Toplevel(parent);self.root.title('BFT Timers' if 'timer' in save_position.__name__ and 'trigger' not in save_position.__name__ else 'BFT Class Alerts');self.root.withdraw();self.root.overrideredirect(True);self.root.attributes('-topmost',True);self.root.configure(bg='#071114')

  self.canvas=tk.Canvas(self.root,bg='#071114',highlightthickness=1,highlightbackground='#b99b52');self.canvas.pack(fill='both',expand=True)

  self.canvas.bind('<ButtonPress-1>',self.begin_drag);self.canvas.bind('<B1-Motion>',self.drag_to);self.canvas.bind('<ButtonRelease-1>',self.end_drag)

 def begin_drag(self,event):

  if self.engine and self.engine.config['move_mode'] and event.y<=30:self.drag=(event.x_root-self.root.winfo_x(),event.y_root-self.root.winfo_y())

 def drag_to(self,event):

  if self.drag and self.game:

   _,gx,gy,gw,gh=self.game;x=min(max(gx,event.x_root-self.drag[0]),gx+max(0,gw-self.root.winfo_width()));y=min(max(gy,event.y_root-self.drag[1]),gy+max(0,gh-self.root.winfo_height()));self.root.geometry('+'+str(x)+'+'+str(y))

 def end_drag(self,event):

  if self.drag and self.game:

   self.drag=None;_,gx,gy,_,_=self.game;self.save_position(max(0,self.root.winfo_x()-gx),max(0,self.root.winfo_y()-gy));self.engine.config['move_mode']=False

   try:self.win.u.SetForegroundWindow(self.game[0])

   except (AttributeError,OSError):pass

 def update(self,game,engine,now):

  self.engine=engine;self.game=game;p=engine.config;snap=engine.snapshot(now);rows=snap['alerts'][:p['rows']];moving=p['move_mode']

  fg=self.win.u.GetForegroundWindow()

  if not game or not p['enabled'] or (fg!=game[0] and not (moving and fg==self.handle)) or (not rows and not moving):self.root.withdraw();return

  if self.drag:return

  _,gx,gy,gw,gh=game;w=min(p['width'],gw);h=min(30+max(1,len(rows))*54,gh);x=min(p['x'],max(0,gw-w));y=min(p['y'],max(0,gh-h))

  self.root.geometry(f'{w}x{h}');self.root.deiconify();self.root.update_idletasks();self.handle=self.win.clickthrough(self.root)

  if moving:self.win.set_style(self.handle,-20,self.win.get_style(self.handle,-20)&~(0x20|0x08000000))

  self.win.u.SetWindowPos(self.handle,ctypes.c_void_p(-1),gx+x,gy+y,w,h,0x0010)

  cv=self.canvas;cv.delete('all');kind=(snap['class'] or 'Class').title();cv.create_text(10,7,text='DRAG HERE TO PLACE' if moving else ('WORLD & RAID TIMERS' if kind=='Timers' else kind.upper()+' ALERTS'),anchor='nw',font=('Consolas',9,'bold'),fill='#d4b363')

  if not rows:cv.create_text(10,39,text='Release to save • return to EQ to position',anchor='nw',fill='#a1babb',font=('Arial',9))

  for i,row in enumerate(rows):

   top=30+i*54;color={'info':'#91c9c1','warn':'#ffd080','danger':'#ff766c'}[row['severity']];message=('TEST • ' if row['test'] else '')+row['message'];max_chars=max(10,(w-26)//8)

   cv.create_rectangle(6,top,w-6,top+49,fill='#102329',outline=color)

   cv.create_text(13,top+5,text=message[:max_chars],anchor='nw',fill=color,font=('Consolas',10,'bold'))

   detail=('~'+format(row['remaining'],'.1f')+'s • ' if row['duration'] else '')+row['detail'];cv.create_text(13,top+25,text=detail[:max_chars+12],anchor='nw',fill='#d5e1df',font=('Arial',8))

   if row['duration']:cv.create_rectangle(8,top+46,8+(w-16)*min(1,row['remaining']/max(1,row['duration'])),top+48,fill=color,outline='')

