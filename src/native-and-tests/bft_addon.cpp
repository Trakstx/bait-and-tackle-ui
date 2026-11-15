#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstring>
#include <cwchar>
#include <shellapi.h>
#include <reshade.hpp>
#include "bft_autostart.hpp"

#pragma pack(push, 1)
struct Feed { unsigned magic, generation; double heartbeat; float dps, damage, seconds, demo; float stats[16]; char target[64]; char identity[64]; float aggro[4]; };
#pragma pack(pop)
static_assert(sizeof(Feed) == 240);
static HANDLE mapping = nullptr;
static const volatile Feed *view = nullptr;
static unsigned last_generation = 0;
static ULONGLONG last_change = 0;

static float hud_position[2] = {8, 4};
static float hud_width = 1100;
static bool position_initialized = false, dragging = false, previous_left = false;
static float grab_x = 0, grab_y = 0;
static std::wstring position_file;
static HMODULE own_module = nullptr;
static float bound(float value, float maximum) {
    return value < 0 ? 0 : (value > maximum ? maximum : value);
}
static void save_position() {
    if (position_file.empty()) return;
    wchar_t text[32];
    swprintf(text, 32, L"%.0f", hud_position[0]);
    WritePrivateProfileStringW(L"Position", L"StripX", text, position_file.c_str());
    swprintf(text, 32, L"%.0f", hud_position[1]);
    WritePrivateProfileStringW(L"Position", L"StripY", text, position_file.c_str());
}
static void move_hud(reshade::api::effect_runtime *runtime) {
    // A hidden strip must not retain a mouse interception/drag region.
    if (view && view->magic == 0x31465442 && view->demo < -1.5f) {
        dragging = false; previous_left = false; return;
    }
    if (!position_initialized) {
        position_file = bft_position_path(own_module);
        if (position_file.empty()) return;
        hud_position[0] = float(GetPrivateProfileIntW(L"Position", L"StripX", 8, position_file.c_str()));
        hud_position[1] = float(GetPrivateProfileIntW(L"Position", L"StripY", 4, position_file.c_str()));
        position_initialized = true;
    }
    HWND window = static_cast<HWND>(runtime->get_hwnd());
    RECT client = {};
    GetClientRect(window, &client);
    hud_width = client.right > 16 ? float(client.right - 16) : 1;

    uint32_t mx = 0, my = 0;
    runtime->get_mouse_cursor_position(&mx, &my);
    POINT mouse = {LONG(mx), LONG(my)};
    const bool left = runtime->is_mouse_button_down(0);
    const bool shift = runtime->is_key_down(VK_SHIFT) || runtime->is_key_down(VK_LSHIFT);
    const bool inside = mouse.x >= hud_position[0] && mouse.x < hud_position[0] + hud_width &&
                        mouse.y >= hud_position[1] && mouse.y < hud_position[1] + 42;
    const bool header = inside && mouse.y < hud_position[1] + 24;
    if (!dragging && left && !previous_left && (shift || header) && inside) {
        dragging = true; grab_x = mouse.x - hud_position[0]; grab_y = mouse.y - hud_position[1];
    }
    if (dragging) {
        if (left) { hud_position[0] = mouse.x - grab_x; hud_position[1] = mouse.y - grab_y; runtime->block_input_next_frame(); }
        else { dragging = false; save_position(); }
    }
    hud_position[0] = bound(hud_position[0], client.right > hud_width ? float(client.right - hud_width) : 0);
    hud_position[1] = bound(hud_position[1], client.bottom > 42 ? float(client.bottom - 42) : 0);
    previous_left = left;
    const bool control = runtime->is_key_down(VK_CONTROL) || runtime->is_key_down(VK_LCONTROL);
    // Ctrl+H and Ctrl+J are owned by the dashboard helper; never open a separate report.
    if (control && runtime->is_key_pressed(VK_F8)) {
        save_position();
        runtime->reload_effect_next_frame("BFT_Test.fx");
    }
}
static void update(reshade::api::effect_runtime *runtime, reshade::api::command_list *,
                   reshade::api::resource_view, reshade::api::resource_view)
{
    bft_autostart();
    move_hud(runtime);
    static ULONGLONG last_map_attempt = 0;
    if (!view && GetTickCount64() - last_map_attempt >= 1000) {
        last_map_attempt = GetTickCount64();
        mapping = OpenFileMappingW(FILE_MAP_READ, FALSE, L"Local\\BFT_HUD_V1");
        if (mapping) {
            view = static_cast<const volatile Feed *>(MapViewOfFile(mapping, FILE_MAP_READ, 0, 0, 4096));
            if (!view) { CloseHandle(mapping); mapping = nullptr; }
        }
    }
    struct RenderValues { float live[4]; float stats[16]; float target[32]; float identity[32]; float aggro[4]; } values = {};
    values.live[3] = -1;
    if (view) {
        unsigned before = view->generation;
        MemoryBarrier();
        Feed copy;
        std::memcpy(&copy, const_cast<const Feed *>(view), sizeof(copy));
        MemoryBarrier();
        if (!(before & 1) && before == view->generation && copy.magic == 0x31465442) {
            if (before != last_generation) { last_generation = before; last_change = GetTickCount64(); }
            if (GetTickCount64() - last_change < 2000) {
                values.live[0] = copy.dps; values.live[1] = copy.damage;
                values.live[2] = copy.seconds; values.live[3] = copy.demo;
                std::memcpy(values.stats, copy.stats, sizeof(copy.stats));
                std::memcpy(values.aggro, copy.aggro, sizeof(copy.aggro));
                for (int i=0;i<32;i++) { values.target[i] = float(static_cast<unsigned char>(copy.target[i])); values.identity[i] = float(static_cast<unsigned char>(copy.identity[i])); }
            }
        }
    }
    runtime->enumerate_uniform_variables(nullptr,
      [](reshade::api::effect_runtime *r, reshade::api::effect_uniform_variable variable, void *context) {
        char source[32] = {};
        if (r->get_annotation_string_from_uniform_variable(variable, "source", source) &&
            std::strcmp(source, "bft_live") == 0)
            r->set_uniform_value_float(variable, static_cast<const RenderValues *>(context)->live, 4);
        else if (std::strcmp(source, "bft_position") == 0)
            r->set_uniform_value_float(variable, hud_position, 2);
        else if (std::strcmp(source, "bft_stats") == 0)
            r->set_uniform_value_float(variable, static_cast<const RenderValues *>(context)->stats, 16);
        else if (std::strcmp(source, "bft_target") == 0)
            r->set_uniform_value_float(variable, static_cast<const RenderValues *>(context)->target, 32);
        else if (std::strcmp(source, "bft_identity") == 0)
            r->set_uniform_value_float(variable, static_cast<const RenderValues *>(context)->identity, 32);
        else if (std::strcmp(source, "bft_aggro") == 0)
            r->set_uniform_value_float(variable, static_cast<const RenderValues *>(context)->aggro, 4);
        else if (std::strcmp(source, "bft_width") == 0)
            r->set_uniform_value_float(variable, &hud_width, 1);
      }, &values);
}

extern "C" __declspec(dllexport) const char *NAME = "BFT HUD data bridge";
extern "C" __declspec(dllexport) const char *DESCRIPTION = "Read-only local log data to a test HUD. No gameplay automation.";
BOOL APIENTRY DllMain(HMODULE module, DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH) {
        own_module = module;
        if (!reshade::register_addon(module)) return FALSE;
        reshade::register_event<reshade::addon_event::reshade_begin_effects>(update);

    } else if (reason == DLL_PROCESS_DETACH) {
        reshade::unregister_addon(module);
        if (view) UnmapViewOfFile(const_cast<const Feed *>(view));
        if (mapping) CloseHandle(mapping);
    }
    return TRUE;
}
