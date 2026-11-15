#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0601
#include <windows.h>
#include "bft_autostart.hpp"
int main(){
 wchar_t expected[2]={};
 if(GetEnvironmentVariableW(L"BFT_TEST_EXPECT_NO_DESKTOP",expected,2)){
  if(GetShellWindow())return 4;
  bool started=bft_start_session();Sleep(600);return started?3:0;
 }
 bft_autostart();bft_autostart();Sleep(600);return 0;
}
