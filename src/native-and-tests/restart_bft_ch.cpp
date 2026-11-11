#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0601
#include <windows.h>
#include <shellapi.h>
#include <string>
#include <cwchar>
// Update only our CH helper, identified by its own hidden root window and exact
// private-runtime executable path. Never enumerate or terminate the game.
int WINAPI wWinMain(HINSTANCE,HINSTANCE,PWSTR,int) {
    wchar_t module[32768]={};GetModuleFileNameW(nullptr,module,32768);
    std::wstring base(module);base=base.substr(0,base.find_last_of(L"\\"));
    std::wstring expected=base+L"\\runtime\\pythonw.exe";
    HWND root=FindWindowW(nullptr,L"BFT CH Chain");
    if(root) {
        DWORD pid=0;GetWindowThreadProcessId(root,&pid);
        HANDLE process=OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION|SYNCHRONIZE|PROCESS_TERMINATE,FALSE,pid);
        if(!process)return 2;
        wchar_t path[32768]={};DWORD length=32768;
        if(!QueryFullProcessImageNameW(process,0,path,&length)||_wcsicmp(expected.c_str(),path)!=0){CloseHandle(process);return 3;}
        PostMessageW(root,WM_CLOSE,0,0);
        if(WaitForSingleObject(process,2000)==WAIT_TIMEOUT) {TerminateProcess(process,0);WaitForSingleObject(process,2000);}
        CloseHandle(process);
    }
    std::wstring args=L"\""+base+L"\\ch_overlay.py\" --settings";
    auto result=ShellExecuteW(nullptr,L"open",expected.c_str(),args.c_str(),base.c_str(),SW_SHOWNORMAL);
    return reinterpret_cast<INT_PTR>(result)>32?0:4;
}
