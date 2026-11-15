#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0601
#include <windows.h>
#include <cstdio>
#include "bft_autostart.hpp"
int main(){
 HANDLE current=nullptr,shell_token=nullptr;bool elevated=false,shell_elevated=true;
 if(!OpenProcessToken(GetCurrentProcess(),TOKEN_QUERY,&current)||!bft_token_elevated(current,elevated))return 5;
 DWORD shell_pid=0,our_session=0,shell_session=0;
 GetWindowThreadProcessId(GetShellWindow(),&shell_pid);
 HANDLE shell=shell_pid?OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION,FALSE,shell_pid):nullptr;
 bool valid_shell=shell && OpenProcessToken(shell,TOKEN_QUERY|TOKEN_DUPLICATE,&shell_token) &&
  bft_same_user(current,shell_token) && bft_token_elevated(shell_token,shell_elevated) && !shell_elevated &&
  ProcessIdToSessionId(GetCurrentProcessId(),&our_session) && ProcessIdToSessionId(shell_pid,&shell_session) && our_session==shell_session;
 bool blocked=elevated&&!valid_shell;
 std::printf("BFT_EXPECT_BLOCKED=%d ELEVATED=%d VALID_DESKTOP_TOKEN=%d\n",blocked,elevated,valid_shell);
 if(shell_token)CloseHandle(shell_token);if(shell)CloseHandle(shell);CloseHandle(current);
 if(blocked){bool started=bft_start_session();Sleep(600);return started?3:0;}
 bft_autostart();bft_autostart();Sleep(600);return 0;
}
