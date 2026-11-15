#pragma once
#include <windows.h>
#include <string>
#include <vector>

inline std::wstring bft_module_path(HMODULE module = nullptr) {
    for (DWORD capacity = 512; capacity <= 32768; capacity *= 2) {
        std::vector<wchar_t> buffer(capacity);
        DWORD length = GetModuleFileNameW(module, buffer.data(), capacity);
        if (!length) return {};
        if (length < capacity) return std::wstring(buffer.data(), length);
    }
    return {}; // Truncation is an error, never a usable path.
}
inline std::wstring bft_sibling_path(const std::wstring &module, const wchar_t *name) {
    const auto slash = module.find_last_of(L"\\/");
    if (module.empty() || slash == std::wstring::npos) return {};
    std::wstring result = module.substr(0, slash + 1) + name;
    return result.size() < 32767 ? result : std::wstring{};
}
