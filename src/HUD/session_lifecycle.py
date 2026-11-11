"""Windows-owned helper tree. The game is deliberately outside this job."""
import ctypes
from ctypes import wintypes as w
import subprocess
import _winapi

k = ctypes.WinDLL('kernel32', use_last_error=True)
k.CloseHandle.argtypes = [w.HANDLE]
k.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
k.CreateJobObjectW.restype = w.HANDLE
k.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
k.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
k.ResumeThread.argtypes = [w.HANDLE]
k.ResumeThread.restype = w.DWORD
k.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
k.OpenProcess.restype = w.HANDLE
k.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
k.QueryFullProcessImageNameW.argtypes = [w.HANDLE, w.DWORD, w.LPWSTR, ctypes.POINTER(w.DWORD)]

class Basic(ctypes.Structure):
    _fields_ = [('per_process', ctypes.c_longlong), ('per_job', ctypes.c_longlong),
        ('flags', w.DWORD), ('minimum', ctypes.c_size_t), ('maximum', ctypes.c_size_t),
        ('active', w.DWORD), ('affinity', ctypes.c_size_t), ('priority', w.DWORD), ('scheduling', w.DWORD)]
class Extended(ctypes.Structure):
    _fields_ = [('basic', Basic), ('io', ctypes.c_ulonglong * 6),
        ('process_memory', ctypes.c_size_t), ('job_memory', ctypes.c_size_t),
        ('peak_process', ctypes.c_size_t), ('peak_job', ctypes.c_size_t)]

def process_path(handle):
    buf = ctypes.create_unicode_buffer(32768); size = w.DWORD(len(buf))
    if not k.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
        raise ctypes.WinError(ctypes.get_last_error())
    return buf.value

class HelperJob:
    def __init__(self):
        self.handle = k.CreateJobObjectW(None, None)
        if not self.handle: raise ctypes.WinError(ctypes.get_last_error())
        limits = Extended(); limits.basic.flags = 0x2000 # KILL_ON_JOB_CLOSE
        if not k.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            error = ctypes.get_last_error(); self.close(); raise ctypes.WinError(error)
    def start(self, args, cwd):
        # Suspend before assignment: children cannot escape between creation and assignment.
        hp, ht, pid, tid = _winapi.CreateProcess(None, subprocess.list2cmdline(args),
            None, None, False, 0x08000004, None, str(cwd), subprocess.STARTUPINFO())
        try:
            if not k.AssignProcessToJobObject(self.handle, int(hp)):
                raise ctypes.WinError(ctypes.get_last_error())
            if k.ResumeThread(int(ht)) == 0xffffffff:
                raise ctypes.WinError(ctypes.get_last_error())
        except BaseException:
            _winapi.TerminateProcess(hp, 1)
            raise
        finally:
            _winapi.CloseHandle(ht); _winapi.CloseHandle(hp)
        return pid
    def close(self):
        if self.handle:
            k.CloseHandle(self.handle); self.handle = None
