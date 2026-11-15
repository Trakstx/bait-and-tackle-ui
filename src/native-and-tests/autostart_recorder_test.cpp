#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string>
int WINAPI wWinMain(HINSTANCE,HINSTANCE,PWSTR,int){
 HANDLE f=CreateFileW(L"record.txt",FILE_APPEND_DATA,FILE_SHARE_READ,nullptr,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
 std::wstring text=std::wstring(GetCommandLineW())+(GetConsoleWindow()?L" CONSOLE\n":L" HIDDEN\n");DWORD n;
 if(f==INVALID_HANDLE_VALUE)return 1;
 WriteFile(f,text.data(),DWORD(text.size()*sizeof(wchar_t)),&n,nullptr);CloseHandle(f);return 0;
}
