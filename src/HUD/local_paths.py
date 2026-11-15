"""Reject network/device paths before any recorder filesystem access."""
import ctypes, os, stat
from pathlib import Path, PureWindowsPath

def local_folder(value, inspect=True):
    raw=str(value).strip()
    if not raw or any(ord(c)<32 for c in raw): raise ValueError('Choose an absolute local folder.')
    normalized=raw.replace('/', '\\')
    windows=PureWindowsPath(normalized)
    if normalized.startswith('\\\\') or not windows.is_absolute() or len(windows.drive)!=2 or windows.drive[1]!=':':
        raise ValueError('Network shares and device paths are not allowed for recordings.')
    reserved=getattr(os.path,'isreserved',lambda p:PureWindowsPath(p).is_reserved())
    if any(':' in part or reserved(part) for part in windows.parts[1:]):raise ValueError('Device/stream paths are not allowed.')
    if os.name!='nt':return Path(raw)
    path=Path(os.path.abspath(normalized))
    if inspect:
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetDriveTypeW.argtypes=[ctypes.c_wchar_p];kernel.GetDriveTypeW.restype=ctypes.c_uint
        if kernel.GetDriveTypeW(path.anchor) not in (2,3):raise ValueError('Use a local fixed or removable drive, not a mapped/network drive.')
        # Check each component without following a junction/symlink to a share.
        current=Path(path.anchor)
        for part in path.parts[1:]:
            current=current/part
            try:info=current.lstat()
            except FileNotFoundError:continue
            if getattr(info,'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise ValueError('Recording folders cannot pass through links or junctions.')
            if not stat.S_ISDIR(info.st_mode):raise ValueError('Recording destination must be a folder.')
    return path
