# Installation and first launch

[Wiki home](README.md) · [Installation](Installation.md) · [Quick reference](Quick-reference.md) · [Troubleshooting](Troubleshooting.md)

## Before you start

Use the playable installer ZIP from [Releases](https://github.com/Trakstx/bait-and-tackle-ui/releases/latest), not GitHub's automatic source archive. The v0.7.0 package is approximately **43.5 MB downloaded and 84 MB extracted**. Backups, caches, saved data and the optional OBS runtime are additional.

Close EQ before installing. Use a working Windows P1999 installation and windowed/borderless mode. A private Python/Tk runtime is included; no separate Python install is necessary.

## Install

1. Download the playable ZIP and extract the **whole folder**.
2. Run **Install Bait and Tackle.cmd**.
3. Approve the expected installer elevation prompt.
4. Select the directory containing `eqgame.exe` if asked. Do not select Logs or uifiles.
5. Wait for installation to finish. The installer verifies files and backs up replacements.
6. Launch through the installed **Play Bait and Tackle** shortcut.
7. Enter `/log on` in EQ.
8. Enter `/loadskin BAIT_AND_FUCKING_TACLE 1`.
9. With EQ in the foreground, press **Ctrl+J**.

## Confirm it worked

The skin should load without a new XML error. The shared dashboard should open and the active character should produce fresh log lines. Enable the panels you need. Loading the skin alone does not start the external helper.

## Reload versus restart

Ordinary helper settings can change while the latest helper is running. Native XML may require a skin reload. Replacing a loaded graphics/HUD component requires closing EQ. Layout copies and graphics-file changes wait for a normal exit so EQ does not overwrite them.

If installation stops, retain the exact error. Do not repeatedly launch duplicate helpers or overwrite a running game. Follow [Troubleshooting](Troubleshooting.md).

---
[All pages](README.md) · [Report a bug](https://github.com/Trakstx/bait-and-tackle-ui/issues/new?template=bug.yml)
