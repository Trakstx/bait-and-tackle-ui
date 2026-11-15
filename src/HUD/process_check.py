"""Read the Windows process list without relying on tasklist or WMI."""
import ctypes
from ctypes import wintypes


def process_still_running(kernel, pid):
    """A listed process may already be signaled during Windows teardown.

    Inaccessible processes remain blockers: absence of permission is not proof
    that it is safe to change game files.
    """
    handle = kernel.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE only
    if not handle:
        return True
    try:
        return kernel.WaitForSingleObject(handle, 0) != 0
    finally:
        kernel.CloseHandle(handle)


def find_game_processes(executable=None):
    from pathlib import Path
    from session_lifecycle import k, process_path
    matches = []
    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD),
            ('th32ProcessID', wintypes.DWORD), ('th32DefaultHeapID', ctypes.c_size_t),
            ('th32ModuleID', wintypes.DWORD), ('cntThreads', wintypes.DWORD),
            ('th32ParentProcessID', wintypes.DWORD), ('pcPriClassBase', wintypes.LONG),
            ('dwFlags', wintypes.DWORD), ('szExeFile', wintypes.WCHAR * 260),
        ]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel.Process32FirstW.restype = wintypes.BOOL
    kernel.Process32NextW.argtypes = kernel.Process32FirstW.argtypes
    kernel.Process32NextW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        ok = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            if entry.szExeFile.casefold() == 'eqgame.exe' and process_still_running(kernel, entry.th32ProcessID):
                if executable is None:
                    matches.append(entry.th32ProcessID)
                else:
                    handle = k.OpenProcess(0x1000, False, entry.th32ProcessID)
                    if handle:
                        try:
                            if Path(process_path(handle)).resolve() == Path(executable).resolve():
                                matches.append(entry.th32ProcessID)
                        finally:
                            k.CloseHandle(handle)
            ok = kernel.Process32NextW(snapshot, ctypes.byref(entry))
        error = ctypes.get_last_error()
        if error not in (0, 18):  # ERROR_NO_MORE_FILES is normal completion.
            raise ctypes.WinError(error)
        return matches
    finally:
        kernel.CloseHandle(snapshot)


def is_game_running():
    return bool(find_game_processes())


if __name__ == '__main__':
    print('EverQuest running:', is_game_running())
