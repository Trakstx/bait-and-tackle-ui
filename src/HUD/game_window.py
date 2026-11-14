"""Identify an EQ window using OS window/process metadata, without reading game memory."""
import ctypes
from ctypes import wintypes as W
from pathlib import Path
from process_check import find_game_processes
from session_lifecycle import k,process_path

def game_window(expected=None,pid=None):
 u=ctypes.WinDLL('user32',use_last_error=True);u.FindWindowW.argtypes=[W.LPCWSTR,W.LPCWSTR];u.FindWindowW.restype=W.HWND;u.GetWindowThreadProcessId.argtypes=[W.HWND,ctypes.POINTER(W.DWORD)]
 hwnd=u.FindWindowW(None,'EverQuest')
 if not hwnd:return None
 actual=W.DWORD();u.GetWindowThreadProcessId(hwnd,ctypes.byref(actual))
 if pid is not None and actual.value!=pid:return None
 if actual.value not in find_game_processes():raise RuntimeError('The EverQuest window could not be matched to an eqgame.exe process.')
 verified=False;image=None;handle=k.OpenProcess(0x1000,False,actual.value)
 if handle:
  try:
   try:image=Path(process_path(handle)).resolve()
   except OSError:image=None
  finally:k.CloseHandle(handle)
 if image is not None:
  if expected is not None and image!=Path(expected).resolve():raise RuntimeError('The open EverQuest is running from '+str(image.parent)+', while this BFT installation uses '+str(Path(expected).parent)+'.')
  verified=True
 return {'hwnd':hwnd,'pid':actual.value,'path_verified':verified,'path':str(image) if image else None}

def window_alive(hwnd,pid):
 u=ctypes.WinDLL('user32',use_last_error=True);u.IsWindow.argtypes=[W.HWND];u.IsWindow.restype=W.BOOL;u.GetWindowThreadProcessId.argtypes=[W.HWND,ctypes.POINTER(W.DWORD)]
 if not u.IsWindow(hwnd):return False
 current=W.DWORD();u.GetWindowThreadProcessId(hwnd,ctypes.byref(current));return current.value==pid
