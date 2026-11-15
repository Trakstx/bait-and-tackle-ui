#pragma once
#include <windows.h>
#include <string>
#include <vector>
#include <shlobj.h>

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

inline std::wstring bft_position_path(HMODULE module) {
    const auto legacy = bft_sibling_path(bft_module_path(module), L"BFT_Position.ini");
    PWSTR folder = nullptr;
    if (FAILED(SHGetKnownFolderPath(FOLDERID_LocalAppData, 0, nullptr, &folder))) return {};
    std::wstring directory = std::wstring(folder) + L"\\BaitAndTackle";
    CoTaskMemFree(folder);
    if (!CreateDirectoryW(directory.c_str(), nullptr) && GetLastError() != ERROR_ALREADY_EXISTS) return {};
    const auto path = directory + L"\\BFT_Position.ini";
    if (path.size() >= 32767) return {};
    // First use preserves the old saved position; never overwrite a newer per-user position.
    if (!legacy.empty() && GetFileAttributesW(path.c_str()) == INVALID_FILE_ATTRIBUTES)
        CopyFileW(legacy.c_str(), path.c_str(), TRUE);
    return path;
}
