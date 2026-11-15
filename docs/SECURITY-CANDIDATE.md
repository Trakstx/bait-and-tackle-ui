# Startup and build security candidate

This branch addresses the review's F1, F2 and F4. It is not a stable release or a finding that every audit issue is resolved. The installed game and public v0.7.0 artifact are not replaced by this work.

## Behavior preserved and changed

- The native skin, shader feed layout, HUD dragging, position INI name, log readers, dashboard, CH/buff/class/raid panels, bank/maps and recorder implementation are retained.
- Python startup uses only the private runtime, DLLs, Lib and application directory. No external game-parent path, current-directory search or automatic `site` customization.
- Play, Refresh, CH and demo native entry points start standard-user helpers. When invoked from elevated EQ, the add-on requests the same desktop user's non-elevated shell token, validates its session/user/elevation, and launches with that user's environment. It never falls back to an elevated helper if this fails.
- Python launcher/refresh/overlay/feeder entry points reject administrator execution. Launch normally from the desktop. Installing into a protected folder may still need approval. An existing elevated legacy helper may require a normal EQ/helper exit before migration; the candidate does not elevate merely to kill it.
- Normal Play launches EQ without elevation first. Only Windows error 740 permits an EQ-only UAC request. The log readers, dashboard/browser and recorder remain standard-user children. Elevated-EQ audio capture and global hotkeys must still pass the live gate below.
- Writable dashboard session data and refresh diagnostics now live under per-user LocalAppData, keyed by installation. The optional OBS engine and portable profile also live in the user recorder cache, not the protected game directory. Its first start may download the verified engine again; saved incident paths and existing clips are unchanged.
- The unauthenticated `pending-autostart.bin` replacement branch is removed.
- The add-on calculates its position path outside DLL initialization using a checked growing buffer and bounded string construction. Truncated/overlong paths fail without a buffer write. Existing short-path position files remain compatible.
- Standalone CH and CH Demo keep their prior entry-point behavior. Restart BFT Settings retains its CH-only restart behavior; Refresh remains the combined helper refresh tool.

## Exact native source map

| Binary | Entry source | Shared source |
|---|---|---|
| BFT_HUD.addon32 | src/native-and-tests/bft_addon.cpp | bft_autostart.hpp, bft_user_process.hpp, bft_paths.hpp; pinned ReShade SDK |
| Play Bait and Tackle.exe | play_bft.cpp | helper_launcher.cpp, bft_user_process.hpp, bft_paths.hpp |
| Refresh Bait and Tackle.exe | refresh_bft.cpp | helper_launcher.cpp, bft_user_process.hpp, bft_paths.hpp |
| Restart BFT Settings.exe | restart_bft_ch.cpp | bft_user_process.hpp, bft_paths.hpp |
| CH Chain.exe | helper_launcher.cpp with ch_overlay.py/settings defines | bft_user_process.hpp, bft_paths.hpp |
| CH Chain Demo.exe | ch_demo_launcher.cpp | helper_launcher.cpp, bft_user_process.hpp, bft_paths.hpp |

`tools/build_native.py` contains every target's arguments. It emits `native-build.json` with source/SDK/compiler and output hashes. Binaries are not Authenticode signed. A build receipt is not an independent security audit.

## Rebuild

On Windows, from the repository root with Python 3.12:

```powershell
python tools/fetch_build_inputs.py --output build/inputs
$compiler = 'build/inputs/compiler/w64devkit/bin/i686-w64-mingw32-g++.exe'
$sdk = 'build/inputs/sdk/reshade-18deaa52de0c425a78b329e9cb3c497281cd00ec/include'
python tools/build_native.py --compiler $compiler --sdk $sdk --output build/native-a
python tools/build_native.py --compiler $compiler --sdk $sdk --output build/native-b
python tools/package_candidate.py --seed build/inputs/vendor-seed.zip --native build/native-a --output build/package
python tools/verify_runtime.py --hud build/package/Bait-and-Tackle/payload/BFT_HUD
```

Use fresh output directories. The workflow builds twice and requires all six output hashes to match, exercises native long-path construction and an inert automatic-startup harness, runs security/lifecycle regressions, verifies imports using the actual embedded interpreter, and verifies the payload manifest. It uploads a candidate artifact only; it does not install, merge or publish a release. The artifact contains the source commit ID, exact application/native source receipts, native sources and hashes.

The frozen v0.7.0 seed supplies the existing runtime/maps/skin/vendor assets by exact archive hash. No old BFT executable is retained: all six are rebuilt, and top-level helper application files come from this commit. The unmodified vendor seed is available from the pinned release URL in `tools/build-inputs.json`. This deliberately retains the old runtime baseline and does not resolve F6. ReShade/vendor binaries are not claimed to be built from BFT source.

## Required live gate before switching the installed version

1. Use a backup/test installation, with EQ closed for binary replacement. Keep the working installation and character settings intact.
2. Test both normal and administrator-required EQ launch; inspect helper, browser and OBS tokens to confirm they remain non-elevated. Test direct eqgame.exe automatic startup too.
3. Verify DPS updates, dragging and saved position, Ctrl+H/J, CH/class/buff/raid panels, class switching and settings saves.
4. Verify game video and process audio, incident hotkey, replay rollover and saved-clip playback while EQ uses its real compatibility settings.
5. Close EQ normally; verify only owned helpers/recorder close. Test refresh without an EQ restart.

No real EQ session is started or closed by the automated suite. On an elevated headless CI host the bootstrap test asserts that no helper is launched; positive automatic startup is tested on the local desktop. The elevated-shell-token path needs an interactive live check. Failure to obtain a standard desktop token fails visibly/diagnostically rather than executing helpers as administrator.

## Still open

Recorder path validation, transactional imports/rollback, runtime refresh, HTTP worker limits and network disclosures remain separate audit work. Build provenance does not establish P1999 staff permission for the graphics integration or visibility modifications. Do not present this candidate as a fully cleared release.
