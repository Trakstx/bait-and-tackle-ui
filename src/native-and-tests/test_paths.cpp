#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0601
#include "bft_paths.hpp"
#include <cassert>
int main() {
    assert(!bft_module_path().empty());
    assert(bft_sibling_path(L"C:\\game\\BFT_HUD.addon32", L"BFT_Position.ini") == L"C:\\game\\BFT_Position.ini");
    std::wstring old = L"C:\\" + std::wstring(240, L'x') + L"\\BFT_HUD.addon32";
    assert(bft_sibling_path(old, L"BFT_Position.ini").size() == 260);
    assert(bft_sibling_path(L"C:\\"+std::wstring(32760,L'x')+L"\\a",L"BFT_Position.ini").empty());
    assert(bft_sibling_path(L"no-directory", L"BFT_Position.ini").empty());
    assert(bft_sibling_path(L"C:\\魚\\a.dll", L"BFT_Position.ini") == L"C:\\魚\\BFT_Position.ini");
}
