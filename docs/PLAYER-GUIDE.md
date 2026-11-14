# Bait & Tackle player guide

Version 0.7.0 preview · Windows · Project 1999

## Start here

Bait & Tackle combines an EverQuest skin with an external log reader, floating displays, and a local HTML dashboard. The native skin loads in EQ. The helper runs beside EQ and supplies the additional panels. Loading the skin alone does not start the helper.

1. Download the playable ZIP from the project's GitHub Releases page. GitHub's automatic source ZIP is not the installer.
2. Extract the entire ZIP. Do not run individual files from inside the archive.
3. Close all EverQuest sessions. Run **Install Bait and Tackle.cmd**.
4. Select the folder containing `eqgame.exe` if the installer asks. Review the Windows elevation prompt.
5. Start EQ through **Play Bait and Tackle**. This starts a session-owned helper.
6. In EQ, enter `/log on`, then `/loadskin BAIT_AND_FUCKING_TACLE 1`.
7. Use windowed or borderless mode. Press **Ctrl+J** while EQ has focus to open the dashboard.

The installer verifies its payload and backs up replaced files. It does not require a system-wide Python installation. Install into your actual EQ directory, not its Logs or uifiles subdirectory.

## Controls and commands

| Control | Purpose |
|---|---|
| Ctrl+J / Ctrl+H | Open the shared HTML dashboard in the current build |
| Ctrl+Shift+F9 | Save the rolling recording as a permanent incident, while the recorder is active |
| `/log on` | Enable the source used by log-based features |
| `/who` | Supply observed character class and level where supported |
| `/outputfile inventory` | Create the inventory snapshot used by bank and equipment tools |
| `/loadskin BAIT_AND_FUCKING_TACLE 1` | Reload the native skin |
| Alt+B | Native buff-window toggle, subject to your EQ key bindings |
| Alt+P | Native group-window toggle, subject to your EQ key bindings |
| Alt+S | Native spell-gem window toggle; melee classes may not expose this window |

EQ key bindings can differ. Do not repeatedly reload the skin to repair a helper process: XML and external panels have separate lifecycles.

## Dashboard reference

### DPS and combat history

The strip shows rolling and fight-based damage statistics from messages visible in the selected character's log. The rolling window is 12 seconds. Configure the fight-end silence timeout and pet names in DPS settings. Pet attribution requires recognizable messages and configured pet names. Missing or filtered messages produce incomplete totals. Generic magic damage cannot always be assigned to a caster. This is a parser, not server combat telemetry.

The reader follows active log activity and character changes. If it follows the wrong character, ensure the current character is logging and producing new lines. Avoid relying on old log modification times alone when diagnosing character identity.

### Complete Heal chain

Configure announcement format, channel, ordered roster, your slot, cast length, cadence, and reset timeout. Test a sample announcement before a raid. A format such as `{slot} CH -- {target}` must match the actual raid call, including its expected structure. The strip estimates timing from announcements; a call is not proof that a heal landed. Resists, fizzles, interrupts, missed calls, and changes in raid convention can invalidate estimates. Agree on one announcement format with the chain leader.

### Aggro estimate

This displays your modeled melee hate, not a server hate list or your percentage against another tank. Run `/outputfile inventory` after changing weapons and `/who` to supply class and level. Item IDs are resolved to weapon data when available. External item data may not match the P1999 era. Procs, taunt jumps, and unsupported abilities are excluded. Never use this display as a guarantee that a tank has established aggro.

### Buff timers

The helper has its own icon-and-timer panel. It reads cast names, landing messages, and wear-off messages. Its stable display order is separate from EQ's native buff slots. It does not determine native slots through screen scanning.

Shared landing text is ambiguous. Configure duration overrides and review inferred entries marked with `?`. Unknown duration is preferable to false precision. Native icons remain the place to click effects off. Silent dispels and manual removal may be missed. Zoning preserves observations and pauses normal loading time. Observed camp countdowns allow logout timing to pause; unclear exits can restore effects with unknown remaining time. Death clears saved observations. JBoots has the configured 18-minute default; it is an estimate unless confirmed by observed events.

### Bank and equipment snapshots

Run `/outputfile inventory` to refresh the snapshot. The bank view is read-only and cannot move items. Click an item to open its P1999 wiki lookup. Snapshots are not a live bank connection. Inspect the character and export time before trusting the display; the export does not reliably identify the server.

### Maps

Browse the bundled Zliz/EQAtlas maps. `/loc` updates the last reported position. Successful Sense Heading immediately before `/loc` can supply direction. This is not continuous GPS. Select dungeon floors manually. Zone and character changes clear stale markers.

### Class alerts and timers

Class alerts use observed identity or a manual class override. Enable only the presets you want. Custom rules support literal text and wildcard matching, class restrictions, severity, short messages, estimated countdowns, and Windows speech. They do not execute game commands. Test each rule with a representative message. Audio uses the selected installed Windows voice. Avoid putting credentials into trigger text or shared profiles.

The timer panel can be moved, collapsed, hidden, and resized. Hiding a panel does not mean its timers stopped. Event timers depend on an observed trigger and are not a server spawn database. Verify the event and delay before relying on a countdown.

### Experience tracking

Automatic sessions and manually named sessions organize observed activity. Log messages can identify kills and experience events, but do not always expose an exact XP percentage. Use checkpoints when precise progress is needed. Do not treat an inferred event count as a measured percentage. The interface limits loaded session history rather than presenting all history at once.

### Misc and layout copy

Server tick display is an estimate synchronized by the helper. Layout copying transfers saved window positions and sizes between characters or named templates. Optional hotkey copying also replaces saved socials and ability assignments. Different classes can have incompatible abilities or spell-gem references. Preview first. Copies are queued until EQ closes normally so the client cannot overwrite the result. Backups are created before target files change.

The graphics visibility fix modifies graphics files and is queued until EQ closes. It does not grant an Ultravision spell. Use its backup/revert control if needed.

### Recorder

The optional recorder uses an isolated portable OBS runtime. On first use it downloads the pinned official OBS package, approximately 224 MB. This runtime is separate from a personal OBS installation.

The intended recording profile is native client size, capped at 1920×1200, 15 FPS, approximately 3 Mbps H.264 video and 96 Kbps audio. It captures the EQ client and its process audio, without a microphone or desktop-wide capture source. Hardware encoding is selected when supported; software fallback can use more CPU.

Unsaved footage rolls through a five-minute RAM buffer. The encoded payload is roughly 116 MB for five minutes at this bitrate, with additional OBS/GPU/process overhead. This is not a hard total-memory cap. Old unsaved footage rolls off automatically. Saving an incident writes an MKV and metadata into the chosen folder. **Saved incidents do not automatically expire.** Choose a folder with sufficient space and manage permanent clips yourself.

Start or stop recording from Recorder. Ctrl+Shift+F9 requests a saved incident while the buffer is active. Wait for the saved filename/status before assuming you have evidence. A recent start contains only footage since recording began. A crash or abrupt exit can lose unsaved RAM footage. Closing the owned EQ session stops its helpers and recorder.

**Validation status:** EQ-only video and an AAC audio track were observed in a prototype. The final single-controller profile, five-minute retention, hotkey, and saved-incident lifecycle still require an end-to-end live check. Do not depend on this preview as your only evidence recorder until that check passes on your PC.

## Updates

Open **Updates & feedback → Check for updates**. Checks happen only when requested. The helper reads the latest published GitHub release. A newer compatible release must include `Bait-and-Tackle-vX.Y.Z.zip` and `SHA256SUMS.txt`. Download update verifies the archive checksum and stages it under `%LOCALAPPDATA%\BaitAndTackle\updates\<version>`.

Close EQ, open the displayed folder, and run the extracted installer. Updates never replace loaded client components in place. Settings stay under LocalAppData; saved incidents remain in their selected folder. A checksum detects mismatch/corruption; it is not an independent signature if the publishing account itself is compromised.

## Feedback without email

Use **Send a feature request** or **Report a bug**. These open structured GitHub Issues forms. You need a GitHub account, not the maintainer's email. Issues and attachments are public. Search existing issues first. Include the installed version, expected behavior, actual behavior, and minimal reproduction steps. Share only sanitized excerpts. Never submit passwords, session URLs containing dashboard tokens, full personal logs, or inventory exports you do not want public.

## Files and privacy

- Installed helper: `<EQ directory>\BFT_HUD`.
- Native skin: `<EQ directory>\uifiles\BAIT_AND_FUCKING_TACLE`.
- Preferences and feature data: `%LOCALAPPDATA%\BaitAndTackle`.
- Installer backups: `<EQ directory>\BFT_HUD\backups`.
- Recordings: the folder chosen in Recorder.
- Dashboard: a token-protected loopback HTTP server on `127.0.0.1`, with a session-specific port. Do not publish its URL.

No analytics or automatic upload is introduced by the update/feedback feature. Opening an external wiki/GitHub link contacts that service. Item lookups, the optional graphics fix, OBS download, and explicit update checks also require network access.

## Compatibility and removal

This is an unofficial community preview, not a statement of P1999 staff approval. The external parsers do not read game memory or automate gameplay. The distribution also contains a graphics/HUD component; users must independently check applicable server rules. No feature promises to evade detection.

To stop the helper, close its owned EQ session. To disable the skin, load your preferred skin. Keep backups before removing files. Restore only the files you intend to restore from the installation backup; do not overwrite newer character settings blindly. Saved incidents and LocalAppData preferences are separate and remain until you remove them.
