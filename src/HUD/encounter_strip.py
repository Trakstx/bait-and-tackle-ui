"""Click-through encounter strip anchored immediately below the DPS strip."""
import ctypes,tkinter as tk
def geometry(game,offset,height=62):
 _,gx,gy,gw,gh=game;w=max(1,gw-16);x=min(max(0,offset[0]),max(0,gw-w));y=min(max(0,offset[1]+46),max(0,gh-height));return gx+x,gy+y,w,min(height,gh)
class EncounterStrip:
 def __init__(self,parent,win):
  self.win=win;self.root=tk.Toplevel(parent);self.root.title('BFT Klandicar');self.root.withdraw();self.root.overrideredirect(True);self.root.attributes('-topmost',True)
  self.canvas=tk.Canvas(self.root,bg='#061014',highlightthickness=1,highlightbackground='#c6a650');self.canvas.pack(fill='both',expand=True)
 def update(self,game,engine,now,offset):
  s=engine.snapshot(now)
  if not game or not s['active'] or self.win.u.GetForegroundWindow()!=game[0]:self.root.withdraw();return
  x,y,w,h=geometry(game,offset);self.root.geometry(f'{w}x{h}');self.root.deiconify();self.root.update_idletasks();handle=self.win.clickthrough(self.root);self.win.u.SetWindowPos(handle,ctypes.c_void_p(-1),x,y,w,h,0x0010)
  cv=self.canvas;cv.delete('all');color={'danger':'#ff786a','warn':'#f1c667','info':'#9bd7cc'}[s['severity']]
  cv.create_text(10,5,text=s.get('boss','KLANDICAR')+(' [MANUAL]' if s['manual'] else ''),anchor='nw',fill='#d6b767',font=('Consolas',10,'bold'))
  cv.create_text(210,5,text=s['message'][:max(10,(w-225)//8)],anchor='nw',fill=color,font=('Consolas',10,'bold'))
  for i,r in enumerate(s['spells']):
   left=10+i*(w//2);label='TIMING UNKNOWN' if r['status']=='unknown' else ('WINDOW OPEN - NOT EXACT' if r['status']=='ready' else '~'+format(r['remaining'],'.1f')+'s TO RECAST WINDOW')
   cv.create_text(left,27,text=r['name'].upper()+': '+label,anchor='nw',fill='#e5ece8',font=('Consolas',9,'bold'))
  cv.create_text(10,46,text='ESTIMATED - missed or immune AEs may not log; no repeated assumed cycles | CTRL+J > Raid alerts',anchor='nw',fill='#8eaaad',font=('Consolas',8))
