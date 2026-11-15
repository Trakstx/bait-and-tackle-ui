#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0601
#include <windows.h>
#include "bft_paths.hpp"
#include "bft_user_process.hpp"
#ifndef BFT_SCRIPT
#error BFT_SCRIPT must identify the fixed bundled Python entry point.
#endif
int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
    auto module = bft_module_path();
    auto script = bft_sibling_path(module, BFT_SCRIPT);
    auto python = bft_sibling_path(module, L"runtime\\pythonw.exe");
    const auto slash = module.find_last_of(L"\\/");
    if (script.empty() || python.empty() || slash == std::wstring::npos) return 1;
    auto directory = module.substr(0, slash);
    std::wstring command = L"\"" + python + L"\" -B \"" + script + L"\"";
#ifdef BFT_DEMO
    command += L" --demo";
#endif
#if defined(BFT_DEMO) || defined(BFT_SETTINGS)
    command += L" --settings";
#endif
    if (bft_launch_user(python, command, directory)) return 0;
    MessageBoxW(nullptr, L"Could not start the standard-user helper. Start this shortcut normally from your desktop account. Keep it inside BFT_HUD with its private runtime.", L"Bait & Tackle", MB_OK | MB_ICONERROR);
    return 2;
}
