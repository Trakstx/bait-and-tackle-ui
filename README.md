# Bait & Tackle UI

A Project 1999 UI skin with a DPS display, a log-based Complete Heal chain strip, and one HTML settings panel.

**First public preview: v0.6.0.** Live raid-chain behavior still needs player validation. This is a community project, not a claim of Project 1999 staff approval.

## Download and install

Download the attached release ZIP from **Releases**, then extract the entire folder.

1. Close EverQuest.
2. Run **Install Bait and Tackle.cmd**. The installer includes a private Python/Tk runtime, verifies the package, backs up replaced files, and asks for your EverQuest folder if necessary.
3. Start with the installed **Play Bait and Tackle** desktop launcher.
4. Enable logging with `/log on`.
5. Select the skin with `/loadskin BAIT_AND_FUCKING_TACLE 1`.

Use windowed or borderless EverQuest; the CH overlay does not support exclusive fullscreen.

## One settings panel

Press **Ctrl+J while EverQuest is foreground** to open the Bait & Tackle HTML settings window.

- **DPS:** fight-end timeout and pet names by character. Rolling DPS uses 12 seconds.
- **CH chain:** announcement format, channel, roster, your slot, cast duration, cadence, idle reset, optional sound, and a sample-call tester.
- **Aggro:** reserved for future settings; current threat estimates are experimental and incomplete.

**Ctrl+H** opens DPS fight history. The CH strip follows the DPS position and passes mouse clicks through.

Example format: `{slot} CH -- {target}` matches `001 CH -- Tankname`. Enter your raid's actual format and chain order. Timers estimate casts from chat announcements; they do not confirm landed heals or reliably account for fizzles or interruptions.

## Personal data

Logs, history, credentials, inventory exports, and personal preferences are not included. Preferences remain under `%LOCALAPPDATA%\BaitAndTackle`. Import/export profiles from the settings panel to share a raid configuration deliberately.

## Updates and feedback

Updates are distributed through GitHub Releases. In-app update checks are planned and are not implemented in this preview. Include version, window resolution, reproduction steps, and a short sanitized log excerpt in bug reports. Do not upload account credentials or complete personal logs.

## Source and notices

`src/` contains custom HUD code, installer and tests. The full skin templates and assets are included in the attached source archive and installer ZIP. The binary release also bundles CPython/Tk and ReShade. See **THIRD_PARTY_NOTICES.md** and the notices inside the download. Existing assets retain their original attribution; this repository does not relicense them as original Bait & Tackle artwork.

## Development checks

Run `python src/native-and-tests/test_chchain.py` and `python src/native-and-tests/test_settings_hub.py` from the repository root. The settings tests use a temporary local HTTP server. The installer source is intended for the assembled release folder, not for running directly from `src/`.
