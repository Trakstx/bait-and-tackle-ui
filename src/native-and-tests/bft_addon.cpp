#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstring>
#include <cwchar>
#include <reshade.hpp>

#pragma pack(push, 1)
struct Feed { unsigned magic, generation; double heartbeat; float dps, damage, seconds, demo; };
#pragma pack(pop)
static_assert(sizeof(Feed) == 32);
static HANDLE mapping = nullptr;
static const volatile Feed *view = nullptr;
static unsigned last_generation = 0;
static ULONGLONG last_change = 0;

static float hud_position[2] = {1250, 710};
static bool position_initialized = false, dragging = false, previous_left = false;
static float grab_x = 0, grab_y = 0;
static wchar_t position_file[MAX_PATH] = {};
static float bound(float value, float maximum) {
    return value < 0 ? 0 : (value > maximum ? maximum : value);
}
static void save_position() {
    wchar_t text[32];
    swprintf(text, 32, L"%.0f", hud_position[0]);
    WritePrivateProfileStringW(L"Position", L"X", text, position_file);
    swprintf(text, 32, L"%.0f", hud_position[1]);
    WritePrivateProfileStringW(L"Position", L"Y", text, position_file);
}
static void move_hud(reshade::api::effect_runtime *runtime) {
    if (!position_initialized) {
        hud_position[0] = float(GetPrivateProfileIntW(L"Position", L"X", 1250, position_file));
        hud_position[1] = float(GetPrivateProfileIntW(L"Position", L"Y", 710, position_file));
        position_initialized = true;
    }
    HWND window = static_cast<HWND>(runtime->get_hwnd());
    RECT client = {};
    GetClientRect(window, &client);
    uint32_t mx = 0, my = 0;
    runtime->get_mouse_cursor_position(&mx, &my);
    POINT mouse = {LONG(mx), LONG(my)};
    const bool left = runtime->is_mouse_button_down(0);
    const bool shift = runtime->is_key_down(VK_SHIFT) || runtime->is_key_down(VK_LSHIFT);
    const bool inside = mouse.x >= hud_position[0] && mouse.x < hud_position[0] + 290 &&
                        mouse.y >= hud_position[1] && mouse.y < hud_position[1] + 82;
    const bool header = inside && mouse.y < hud_position[1] + 12;
    if (!dragging && left && !previous_left && (shift || header) && inside) {
        dragging = true; grab_x = mouse.x - hud_position[0]; grab_y = mouse.y - hud_position[1];
    }
    if (dragging) {
        if (left) { hud_position[0] = mouse.x - grab_x; hud_position[1] = mouse.y - grab_y; runtime->block_input_next_frame(); }
        else { dragging = false; save_position(); }
    }
    hud_position[0] = bound(hud_position[0], client.right > 290 ? float(client.right - 290) : 0);
    hud_position[1] = bound(hud_position[1], client.bottom > 82 ? float(client.bottom - 82) : 0);
    previous_left = left;
    if ((runtime->is_key_down(VK_CONTROL) || runtime->is_key_down(VK_LCONTROL)) && runtime->is_key_pressed(VK_F8)) {
        save_position();
        runtime->reload_effect_next_frame("BFT_Test.fx");
    }
}
static void update(reshade::api::effect_runtime *runtime, reshade::api::command_list *,
                   reshade::api::resource_view, reshade::api::resource_view)
{
    move_hud(runtime);
    if (!view) {
        mapping = OpenFileMappingW(FILE_MAP_READ, FALSE, L"Local\\BFT_HUD_V1");
        if (mapping) {
            view = static_cast<const volatile Feed *>(MapViewOfFile(mapping, FILE_MAP_READ, 0, 0, 4096));
            if (!view) { CloseHandle(mapping); mapping = nullptr; }
        }
    }
    float values[4] = {0, 0, 0, -1};
    if (view) {
        unsigned before = view->generation;
        MemoryBarrier();
        Feed copy;
        std::memcpy(&copy, const_cast<const Feed *>(view), sizeof(copy));
        MemoryBarrier();
        if (!(before & 1) && before == view->generation && copy.magic == 0x31465442) {
            if (before != last_generation) { last_generation = before; last_change = GetTickCount64(); }
            if (GetTickCount64() - last_change < 2000) {
                values[0] = copy.dps; values[1] = copy.damage;
                values[2] = copy.seconds; values[3] = copy.demo;
            }
        }
    }
    runtime->enumerate_uniform_variables(nullptr,
      [](reshade::api::effect_runtime *r, reshade::api::effect_uniform_variable variable, void *context) {
        char source[32] = {};
        if (r->get_annotation_string_from_uniform_variable(variable, "source", source) &&
            std::strcmp(source, "bft_live") == 0)
            r->set_uniform_value_float(variable, static_cast<const float *>(context), 4);
        else if (std::strcmp(source, "bft_position") == 0)
            r->set_uniform_value_float(variable, hud_position, 2);
      }, values);
}

extern "C" __declspec(dllexport) const char *NAME = "BFT HUD data bridge";
extern "C" __declspec(dllexport) const char *DESCRIPTION = "Read-only local log data to a test HUD. No gameplay automation.";
BOOL APIENTRY DllMain(HMODULE module, DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH) {
        GetModuleFileNameW(module, position_file, MAX_PATH);
        wchar_t *last = wcsrchr(position_file, L'\\');
        if (last) wcscpy(last + 1, L"BFT_Position.ini");
        if (!reshade::register_addon(module)) return FALSE;
        reshade::register_event<reshade::addon_event::reshade_begin_effects>(update);

    } else if (reason == DLL_PROCESS_DETACH) {
        reshade::unregister_addon(module);
        if (view) UnmapViewOfFile(const_cast<const Feed *>(view));
        if (mapping) CloseHandle(mapping);
    }
    return TRUE;
}
