# Privacy, files and cleanup

[Wiki home](README.md) · [Installation](Installation.md) · [Quick reference](Quick-reference.md) · [Troubleshooting](Troubleshooting.md)

The helper dashboard uses loopback (`127.0.0.1`), a session-specific port and token. Keep its full URL private.

| Location | Purpose |
|---|---|
| `<EQ>\BFT_HUD` | Helper, runtime and graphics components |
| `<EQ>\uifiles\BAIT_AND_FUCKING_TACLE` | Native skin |
| `%LOCALAPPDATA%\BaitAndTackle` | Preferences, caches, observations, updates |
| `<EQ>\BFT_HUD\backups` | Installer backups |
| Recorder-selected folder | Permanent MKV incidents and metadata |

## Network activity

No analytics or automatic personal log/recording upload is introduced. Explicit updates contact GitHub. Optional runtime/graphics downloads, item/icon lookups and enabled shared timers contact external services. Clicking wiki/feedback links opens those sites. Windows speech is local.

## Session ownership

The combined launcher owns its helper process tree. Closing its selected EQ session stops owned helpers and the recorder rather than leaving a permanent watcher. Unrelated applications and a personal OBS instance must remain untouched.

## Documentation privacy

Screenshots use the real dashboard with isolated demonstration characters and synthetic data. They do not publish personal logs, chat, credentials or session URLs. An example countdown is not proof of live server behavior.

## Rules and removal

This unofficial preview does not claim P1999 staff approval. Parsers do not expose server-only state or automate gameplay; the distribution also includes a graphics/HUD component. Review applicable rules independently. No detection-evasion claim is made.

Close EQ to stop owned helpers. Load another skin to stop using native XML. Keep backups before removing/restoring installed files. Personal preferences and saved incidents remain separate until removed.

---
[All pages](README.md) · [Report a bug](https://github.com/Trakstx/bait-and-tackle-ui/issues/new?template=bug.yml)
