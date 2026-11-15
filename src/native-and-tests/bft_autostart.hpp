// Launch the external session helper once, after DLL initialization has finished.
// No gameplay memory access, permanent watcher, or command window.
#pragma once
#include <string>
#include "bft_paths.hpp"
#include "bft_user_process.hpp"
inline bool bft_start_session() {
    std::wstring game = bft_module_path();
    if (game.empty()) return false;
    size_t slash = game.find_last_of(L"\\/");
    if (slash == std::wstring::npos || _wcsicmp(game.c_str()+slash+1,L"eqgame.exe") != 0) return false;
    game.resize(slash);
    std::wstring base = game + L"\\BFT_HUD";
    std::wstring python = base + L"\\runtime\\pythonw.exe";
    std::wstring launcher = base + L"\\launcher.py";
    if (GetFileAttributesW(python.c_str()) == INVALID_FILE_ATTRIBUTES ||
        GetFileAttributesW(launcher.c_str()) == INVALID_FILE_ATTRIBUTES) return false;
    std::wstring command = L"\""+python+L"\" -B \""+launcher+L"\" --attach-only --game-pid "+std::to_wstring(GetCurrentProcessId());
    return bft_launch_user(python, command, base);
}
inline void bft_autostart() {
    static bool attempted=false;
    if (attempted) return;
    attempted=true;
    if (!bft_start_session()) OutputDebugStringW(L"Bait & Tackle: automatic session startup unavailable. Use the Play shortcut normally from your desktop to diagnose installation.\n");
}
