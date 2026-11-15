#pragma once
#include <windows.h>
#include <userenv.h>
#include <string>
#include <vector>

inline bool bft_token_elevated(HANDLE token, bool &elevated) {
    TOKEN_ELEVATION value = {}; DWORD size = 0;
    if (!GetTokenInformation(token, TokenElevation, &value, sizeof(value), &size)) return false;
    elevated = value.TokenIsElevated != 0; return true;
}
inline bool bft_same_user(HANDLE first, HANDLE second) {
    DWORD a = 0, b = 0;
    GetTokenInformation(first, TokenUser, nullptr, 0, &a);
    GetTokenInformation(second, TokenUser, nullptr, 0, &b);
    if (!a || !b) return false;
    std::vector<BYTE> av(a), bv(b);
    return GetTokenInformation(first, TokenUser, av.data(), a, &a) &&
           GetTokenInformation(second, TokenUser, bv.data(), b, &b) &&
           EqualSid(reinterpret_cast<TOKEN_USER *>(av.data())->User.Sid,
                    reinterpret_cast<TOKEN_USER *>(bv.data())->User.Sid);
}
// Standard desktop token only. Failure never falls back to an elevated helper.
inline bool bft_launch_user(const std::wstring &executable, std::wstring command,
                            const std::wstring &directory) {
    STARTUPINFOW startup = {}; startup.cb = sizeof(startup);
    startup.dwFlags = STARTF_USESHOWWINDOW; startup.wShowWindow = SW_HIDE;
    PROCESS_INFORMATION process = {};
    HANDLE current = nullptr;
    if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &current)) return false;
    bool elevated = false;
    if (!bft_token_elevated(current, elevated)) { CloseHandle(current); return false; }
    BOOL ok = FALSE;
    if (!elevated) {
        ok = CreateProcessW(executable.c_str(), command.data(), nullptr, nullptr, FALSE,
                            CREATE_NO_WINDOW, nullptr, directory.c_str(), &startup, &process);
    } else {
        DWORD shell_pid = 0, our_session = 0, shell_session = 0;
        GetWindowThreadProcessId(GetShellWindow(), &shell_pid);
        if (!shell_pid || !ProcessIdToSessionId(GetCurrentProcessId(), &our_session) ||
            !ProcessIdToSessionId(shell_pid, &shell_session) || our_session != shell_session) {
            CloseHandle(current); return false;
        }
        HANDLE shell = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, shell_pid);
        HANDLE token = nullptr, primary = nullptr;
        LPVOID environment = nullptr;
        bool shell_elevated = true;
        if (shell && OpenProcessToken(shell, TOKEN_QUERY | TOKEN_DUPLICATE, &token) &&
            bft_same_user(current, token) && bft_token_elevated(token, shell_elevated) &&
            !shell_elevated && DuplicateTokenEx(token, TOKEN_QUERY | TOKEN_DUPLICATE | TOKEN_ASSIGN_PRIMARY,
                nullptr, SecurityImpersonation, TokenPrimary, &primary) &&
            CreateEnvironmentBlock(&environment, primary, FALSE)) {
            ok = CreateProcessWithTokenW(primary, LOGON_WITH_PROFILE, executable.c_str(), command.data(),
                 CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT, environment, directory.c_str(), &startup, &process);
        }
        if (environment) DestroyEnvironmentBlock(environment);
        if (primary) CloseHandle(primary);
        if (token) CloseHandle(token);
        if (shell) CloseHandle(shell);
    }
    CloseHandle(current);
    if (ok) { CloseHandle(process.hThread); CloseHandle(process.hProcess); }
    return ok != FALSE;
}
