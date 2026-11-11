#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <string>
int WINAPI wWinMain(HINSTANCE,HINSTANCE,PWSTR,int) {
    wchar_t path[32768]={}; GetModuleFileNameW(nullptr,path,32768);
    std::wstring base(path); base=base.substr(0,base.find_last_of(L"\\"));
    std::wstring python=base+L"\\runtime\\pythonw.exe";
    std::wstring args=L"\""+base+L"\\ch_overlay.py\" --settings";
#ifdef CH_DEMO
    args+=L" --demo";
#endif
    auto result=ShellExecuteW(nullptr,L"open",python.c_str(),args.c_str(),base.c_str(),SW_SHOWNORMAL);
    return reinterpret_cast<INT_PTR>(result)>32?0:1;
}
