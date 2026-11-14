"""Refresh BFT's external helper job without closing or restarting EverQuest."""
import ctypes,os,subprocess,sys,hashlib
from ctypes import wintypes as W
from pathlib import Path
from process_check import find_game_processes
from session_lifecycle import k,process_path

def parent_pid(pid):
 class Entry(ctypes.Structure):
  _fields_=[('size',W.DWORD),('usage',W.DWORD),('pid',W.DWORD),('heap',ctypes.c_size_t),('module',W.DWORD),('threads',W.DWORD),('parent',W.DWORD),('priority',W.LONG),('flags',W.DWORD),('exe',W.WCHAR*260)]
 k.CreateToolhelp32Snapshot.argtypes=[W.DWORD,W.DWORD];k.CreateToolhelp32Snapshot.restype=W.HANDLE;k.Process32FirstW.argtypes=[W.HANDLE,ctypes.POINTER(Entry)];k.Process32NextW.argtypes=k.Process32FirstW.argtypes
 snap=k.CreateToolhelp32Snapshot(2,0)
 if snap==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
 try:
  e=Entry();e.size=ctypes.sizeof(e);ok=k.Process32FirstW(snap,ctypes.byref(e))
  while ok:
   if e.pid==pid:return e.parent
   ok=k.Process32NextW(snap,ctypes.byref(e))
 finally:k.CloseHandle(snap)
 return None

def helper_script(handle):
 # OS command-line metadata of our own Python helper only; never queried for EQ.
 class UnicodeString(ctypes.Structure):
  _fields_=[('length',W.USHORT),('maximum',W.USHORT),('buffer',ctypes.c_void_p)]
 nt=ctypes.WinDLL('ntdll');nt.NtQueryInformationProcess.argtypes=[W.HANDLE,W.ULONG,ctypes.c_void_p,W.ULONG,ctypes.POINTER(W.ULONG)];nt.NtQueryInformationProcess.restype=W.LONG
 needed=W.ULONG();nt.NtQueryInformationProcess(handle,60,None,0,ctypes.byref(needed))
 if not 1<=needed.value<=131072:raise RuntimeError('Cannot verify the helper command line.')
 data=ctypes.create_string_buffer(needed.value)
 if nt.NtQueryInformationProcess(handle,60,data,len(data),ctypes.byref(needed))<0:raise RuntimeError('Cannot read helper launch metadata.')
 value=UnicodeString.from_buffer(data);command=ctypes.wstring_at(value.buffer,value.length//2)
 shell=ctypes.WinDLL('shell32');shell.CommandLineToArgvW.argtypes=[W.LPCWSTR,ctypes.POINTER(ctypes.c_int)];shell.CommandLineToArgvW.restype=ctypes.POINTER(W.LPWSTR);argc=ctypes.c_int();argv=shell.CommandLineToArgvW(command,ctypes.byref(argc))
 if not argv:raise RuntimeError('Cannot parse helper launch metadata.')
 try:
  for i in range(1,argc.value):
   arg=argv[i]
   if arg in ['-u','-B','-s','-S','-E','-I','-O','-OO']:continue
   if arg.startswith('-'):break
   return Path(arg).resolve()
 finally:
  ctypes.windll.kernel32.LocalFree.argtypes=[ctypes.c_void_p];ctypes.windll.kernel32.LocalFree(argv)
 raise RuntimeError('The helper is not running a verifiable script.')

def trusted_legacy_loader(script,base):
 if script.name.casefold()!='bait-and-tackle-auto-launcher.py':return False
 import ast
 try:
  tree=ast.parse(script.read_text(encoding='utf-8-sig'))
  for node in tree.body:
   if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id=='base':
    if not isinstance(node.value,ast.Call) or not node.value.args or not isinstance(node.value.args[0],ast.Constant) or Path(node.value.args[0].value).resolve()!=base.resolve():return False
    node.value.args[0].value=str(base)
  expected=ast.parse("import sys, runpy\nfrom pathlib import Path\nbase = Path("+repr(str(base))+")\nsys.path.insert(0, str(base))\nrunpy.run_path(str(base / 'launcher.py'), run_name='__main__')\n")
  return ast.dump(tree)==ast.dump(expected)
 except (OSError,ValueError,SyntaxError,TypeError):return False

def verified_handle(pid,expected,script=None):
 if not pid or pid==os.getpid():raise RuntimeError('Invalid helper process.')
 handle=k.OpenProcess(0x101001,False,pid)
 if not handle:raise ctypes.WinError(ctypes.get_last_error())
 try:
  actual=Path(process_path(handle)).resolve()
  if script is None:
   if actual!=Path(expected).resolve():raise RuntimeError('The selected process is not the private BFT helper runtime.')
  else:
   if actual.name.casefold() not in ['python.exe','pythonw.exe']:raise RuntimeError('The selected helper is not a Python process.')
   running=helper_script(handle);wanted=Path(script).resolve();log('helper pid='+str(pid)+' runtime='+str(actual)+' script='+str(running))
   if running!=wanted and not (wanted.name=='launcher.py' and trusted_legacy_loader(running,wanted.parent)):raise RuntimeError('The selected Python process is not running the expected BFT script.')
  return handle
 except Exception:k.CloseHandle(handle);raise

def stop_helpers(overlay_pid,base,game_pid):
 expected=Path(base)/'runtime/pythonw.exe'
 if overlay_pid==game_pid:raise RuntimeError('Refusing to target EverQuest.')
 child=verified_handle(overlay_pid,expected,Path(base)/'ch_overlay.py');owner=None
 try:
  parent=parent_pid(overlay_pid)
  if parent and parent not in [game_pid,os.getpid()]:
   try:owner=verified_handle(parent,expected,Path(base)/'launcher.py')
   except (OSError,RuntimeError):owner=None
  mutex_name='Local\\BFT_Session_'+hashlib.sha256(str(Path(base).parent.resolve()).casefold().encode()).hexdigest()[:24]
  k.OpenMutexW.argtypes=[W.DWORD,W.BOOL,W.LPCWSTR];k.OpenMutexW.restype=W.HANDLE
  mutex=k.OpenMutexW(0x100000,False,mutex_name)
  if mutex:
   k.CloseHandle(mutex)
   if owner is None:raise RuntimeError('Could not verify the BFT session owner; no helper was stopped. Close the older standalone helpers and try again.')
  k.TerminateProcess.argtypes=[W.HANDLE,W.UINT];k.TerminateProcess.restype=W.BOOL
  target=owner or child
  if not k.TerminateProcess(target,0):raise ctypes.WinError(ctypes.get_last_error())
  if k.WaitForSingleObject(target,5000)!=0:raise RuntimeError('The old helper did not finish closing.')
  k.WaitForSingleObject(child,5000)
 finally:
  if owner:k.CloseHandle(owner)
  k.CloseHandle(child)

def log(text):
 try:
  from datetime import datetime
  path=Path(__file__).resolve().parent/'refresh-diagnostics.log'
  with path.open('a',encoding='utf-8') as output:output.write(datetime.now().isoformat()+' '+str(text)+'\n')
 except OSError:pass

def visible_game_pid(expected):
 from game_window import game_window
 info=game_window(expected)
 if info:log('visible EQ '+str(info));return info['pid']
 return None

def select_game(expected):
 visible=visible_game_pid(expected)
 if visible:return visible
 matches=find_game_processes(expected);log('fallback EQ matches='+str(matches))
 if len(matches)==1:return matches[0]
 if not matches:raise RuntimeError('No EverQuest window or matching process was found. Keep EQ open, then run this refresh again.')
 raise RuntimeError('Multiple matching EverQuest processes were found without a visible window. Bring the intended EQ window to the desktop and try again.')

def refresh(base):
 base=Path(base).resolve();game=base.parent;game_pid=select_game(game/'eqgame.exe');log('refresh target EQ pid='+str(game_pid))
 u=ctypes.WinDLL('user32',use_last_error=True);u.FindWindowW.argtypes=[W.LPCWSTR,W.LPCWSTR];u.FindWindowW.restype=W.HWND;u.GetWindowThreadProcessId.argtypes=[W.HWND,ctypes.POINTER(W.DWORD)]
 window=u.FindWindowW(None,'BFT CH Chain')
 if window:
  pid=W.DWORD();u.GetWindowThreadProcessId(window,ctypes.byref(pid));log('overlay pid='+str(pid.value));stop_helpers(pid.value,base,game_pid)
 args=[str(base/'runtime/pythonw.exe'),str(base/'launcher.py'),'--attach-only','--game-pid',str(game_pid),'--settings']
 subprocess.Popen(args,cwd=base,creationflags=subprocess.CREATE_NO_WINDOW);log('new helper session requested')

def main():
 base=Path(__file__).resolve().parent
 if not ctypes.windll.shell32.IsUserAnAdmin():
  result=ctypes.windll.shell32.ShellExecuteW(None,'runas',str(base/'runtime/pythonw.exe'),subprocess.list2cmdline([str(Path(__file__).resolve())]),str(base),0)
  if result<=32:raise RuntimeError('Windows did not authorize refreshing the BFT helpers.')
  return
 log('starting with python='+sys.executable+' elevated='+str(bool(ctypes.windll.shell32.IsUserAnAdmin())))
 refresh(base)
if __name__=='__main__':
 try:main()
 except Exception as exc:
  log('ERROR '+str(exc))
  ctypes.windll.user32.MessageBoxW(None,str(exc),'Bait & Tackle helper refresh',0x10)
