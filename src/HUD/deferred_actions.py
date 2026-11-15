"""Bounded post-session maintenance; no permanent watcher or game input."""
import json,time
from pathlib import Path
from process_check import find_game_processes
from vision_fix import VisionFix
from layout_tools import LayoutService

def run(game,runtime,wait_seconds=0):
 runtime=Path(runtime);vision=VisionFix(game,runtime);events=[]
 def record(action,**details):
  events.append(dict(at=time.time(),action=action,**details))
 def report():
  try:
   runtime.mkdir(parents=True,exist_ok=True);path=runtime/'maintenance-status.json';temp=path.with_suffix('.tmp');temp.write_text(json.dumps(events,indent=2),encoding='utf-8');temp.replace(path)
  except OSError:pass
  return events
 try:
  deadline=time.monotonic()+max(0,min(10,wait_seconds))
  while True:
   pids=find_game_processes()
   if not pids or time.monotonic()>=deadline:break
   time.sleep(.2)
 except OSError as exc:
  record('preflight',ok=False,error=str(exc));return report()
 if pids:
  reason='Waiting for running EverQuest process(es): '+', '.join(map(str,pids))
  try:
   state=vision.state()
   if state.get('pending'):state['blocked']=reason;vision.save(state)
  except OSError as exc:record('vision-status',ok=False,error=str(exc))
  record('preflight',ok=False,blocked=reason);return report()
 # Vision is independent of layout/XP cleanup; one failure cannot skip the other.
 for name,operation in [('vision',vision.apply_pending),('layouts',lambda:LayoutService(game,runtime/'layouts').apply_pending())]:
  try:
   operation()
   if name=='vision':
    state=vision.state();record(name,ok=not bool(state.get('error')),pending=state.get('pending'),error=state.get('error'),applied=state.get('applied',False))
   else:record(name,ok=True)
  except Exception as exc:record(name,ok=False,error=str(exc))
 return report()
