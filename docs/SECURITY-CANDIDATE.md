# Security remediation candidate

This branch implements the technical remediations for F1–F9, with validation limits described below. It is not a stable release or an independent finding that every audit issue is closed. The installed game and public v0.7.0 artifact are not replaced by this work.

## Behavior preserved and changed

- The native skin, shader feed layout, HUD dragging, position INI name, log readers, dashboard, CH/buff/class/raid panels, bank/maps and recorder implementation are retained.
- Python startup uses only the private runtime, DLLs, Lib and application directory. No external game-parent path, current-directory search or automatic `site` customization.
- Play, Refresh, CH and demo native entry points start standard-user helpers. When invoked from elevated EQ, the add-on requests the same desktop user's non-elevated shell token, validates its session/user/elevation, and launches with that user's environment. It never falls back to an elevated helper if this fails.
- Python launcher/refresh/overlay/feeder entry points reject administrator execution. Launch normally from the desktop. Installing into a protected folder may still need approval. An existing elevated legacy helper may require a normal EQ/helper exit before migration; the candidate does not elevate merely to kill it.
- Normal Play launches EQ without elevation first. Only Windows error 740 permits an EQ-only UAC request. The log readers, dashboard/browser and recorder remain standard-user children. Elevated-EQ audio capture and global hotkeys must still pass the live gate below.
- Writable dashboard session data and refresh diagnostics now live under per-user LocalAppData, keyed by installation. The optional OBS engine and portable profile also live in the user recorder cache, not the protected game directory. Its first start may download the verified engine again; saved incident paths and existing clips are unchanged.
- The unauthenticated `pending-autostart.bin` replacement branch is removed.
- The add-on calculates its position path outside DLL initialization using checked growing buffers and bounded strings. Truncated/overlong paths fail without a buffer write. Saved HUD position migrates on first use from the legacy game-folder INI to `%LOCALAPPDATA%/BaitAndTackle/BFT_Position.ini`; an existing per-user position is preserved. The Python strip anchor reads the same new path with legacy fallback, so saving a drag no longer needs game-folder write permission.
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

On Windows, from the repository root with Python 3.14:

```powershell
python tools/fetch_build_inputs.py --output build/inputs
$compiler = 'build/inputs/compiler/w64devkit/bin/i686-w64-mingw32-g++.exe'
$sdk = 'build/inputs/sdk/reshade-18deaa52de0c425a78b329e9cb3c497281cd00ec/include'
python tools/build_native.py --compiler $compiler --sdk $sdk --output build/native-a
python tools/build_native.py --compiler $compiler --sdk $sdk --output build/native-b
python tools/build_runtime.py --cache build/runtime-inputs --output build/runtime
python tools/package_candidate.py --seed build/inputs/vendor-seed.zip --native build/native-a --output build/package --runtime build/runtime
python tools/verify_runtime.py --hud build/package/Bait-and-Tackle/payload/BFT_HUD
```

Use fresh output directories. The workflow builds twice and requires all six output hashes to match, exercises native long-path construction and an inert automatic-startup harness, runs security/lifecycle regressions, verifies imports using the actual embedded interpreter, and verifies the payload manifest. It uploads a candidate artifact only; it does not install, merge or publish a release. The artifact contains the source commit ID, exact application/native source receipts, native sources and hashes.

The frozen v0.7.0 seed supplies existing maps/skin/artwork/ReShade assets by exact archive hash. Its old runtime and all six BFT binaries are replaced. The candidate bundles official, hash-pinned Python 3.14.10 and matching Tcl/Tk, with the vendor SPDX and a generated dependency inventory. ReShade/vendor binaries are not claimed to be built from BFT source. See [dependencies](DEPENDENCIES.md).

## Remaining audit implementation

| Finding | Candidate change | Validation and limits |
|---|---|---|
| F1: startup search/elevation | Private runtime paths; standard-user helpers; no elevated fallback | Startup canary and privilege tests; elevated interactive EQ still needs live test |
| F2: source/build mismatch | Exact six-target source map, pinned toolchain, two-build comparison, CI provenance | Source/output hashes; vendor assets identified separately; unsigned binaries |
| F3: recording destination | Normalize first; reject UNC/device/mapped-drive/reparse/ADS/reserved paths | Lexical and filesystem tests; fixed/removable local storage only |
| F4: unchecked native paths | Checked growing module paths and bounded construction | Native long-path tests; no exploit or formal memory-safety claim |
| F5: partial mutations/recovery | Stage complete sets; external backups; durable journals; conflict-aware restore | Injected failures for installer, layouts and graphics; fresh-install/upgrade restore tests |
| F6: old runtime | Official Python 3.14.10 + matching Tcl/Tk, minimal payload and vendor SPDX | Tests run again in packaged interpreter; runtime versions/imports checked; no zero-CVE claim |
| F7: destructive failed import | Validate and preview before changing controls; rollback UI state on render failure | API preview test plus real settings.js DOM-state regression; Save remains explicit |
| F8: unbounded HTTP resources | Worker cap, read timeout, total connection deadline | Slow-header test and existing authentication/Origin API tests; loopback only |
| F9: undisclosed optional networking | Separate opt-ins default off; visible disclosures; explicit updates/recording | No-network-without-consent test; [network details](NETWORK-PRIVACY.md) |

Cached OBS files are verified against the pinned vendor archive before use; unexpected executable/script additions fail closed. Update downloads use unique staging directories. A supplied game PID must match this installation's executable before it can own a helper session. Installer and recovery CMD files verify the payload before executing private Python. See [recovery instructions](RECOVERY.md).

## Required live gate before switching the installed version

1. Use a backup/test installation, with EQ closed for binary replacement. Keep the working installation and character settings intact.
2. Test both normal and administrator-required EQ launch; inspect helper, browser and OBS tokens to confirm they remain non-elevated. Test direct eqgame.exe automatic startup too.
3. Verify DPS updates, dragging and saved position, Ctrl+H/J, CH/class/buff/raid panels, class switching and settings saves.
4. Verify game video and process audio, incident hotkey, replay rollover and saved-clip playback while EQ uses its real compatibility settings.
5. Close EQ normally; verify only owned helpers/recorder close. Test refresh without an EQ restart.

No real EQ session is started or closed by the automated suite. On an elevated headless CI host the bootstrap test asserts that no helper is launched; positive automatic startup is tested on the local desktop. The elevated-shell-token path needs an interactive live check. Failure to obtain a standard desktop token fails visibly/diagnostically rather than executing helpers as administrator.

## Release gates and unresolved external decisions

Automated tests do not establish actual game rendering, elevated-game audio capture, hotkey behavior, or P1999 staff permission. Complete the live gate above on a separate copy before replacing the working installation. Keep the PR a draft and candidate artifacts separate from stable updates until then. The old public v0.7.0 download is unchanged by this branch and must not be represented as containing these fixes.

The existing release was described as a preview but its GitHub release flag requires maintainer review. Future candidates are marked candidate in the manifest/dashboard and this workflow only uploads Actions artifacts; it cannot publish a stable release. Do not merge or publish automatically as part of testing.

For staff clarification, describe the actual features: native ReShade integration, read-only local log parsing, external overlays/hotkeys, graphics/visibility changes, optional map display and recording. Ask staff about these specific behaviors and distribution, with source links. No staff approval is inferred from other tools, and no message is sent by this work.
