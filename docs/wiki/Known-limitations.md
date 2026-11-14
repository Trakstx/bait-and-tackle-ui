# Known limitations and validation status

[Wiki home](README.md) · [Installation](Installation.md) · [Quick reference](Quick-reference.md) · [Troubleshooting](Troubleshooting.md)

Screenshots show real settings with sample data; they do not establish live raid correctness.

| Feature | Available | Boundary |
|---|---|---|
| DPS | Rolling/fight parsing and history | Missing lines, attribution and fight boundaries |
| CH | Configurable call parsing/timing | Not landed-heal confirmation |
| Aggro | Personal modeled melee hate | No server table, rival-tank percent or complete abilities/procs |
| Buffs | Observations, inference and helper order | No native slot discovery; silent removals can be missed |
| Bank | Read-only exported layout/register | Snapshot freshness and server ambiguity |
| Maps | Atlas and last reported /loc | No continuous GPS; manual floors/calibration |
| Class alerts | Class restrictions and text/wildcard rules | Recognized logged events only |
| Timers | Manual/local/optional shared estimates | Trigger source and schedule accuracy |
| XP | Sessions, events and checkpoints | Exact awards often not in logs |
| Native bags | Styled native containers | Client-controlled hit regions and capacity |
| Recorder | Rolling-buffer integration/save controls | Final single-controller live profile, rollover, hotkey and audio lifecycle test pending |
| Updates | Published release/checksum/extraction | Installer still requires EQ closed |

The public v0.7.0 updater was tested by detecting, downloading, hashing and extracting the published package, then running its installer verification. This is not a fresh-install/gameplay test on every PC.

Before a raid, test actual call formats, character detection, class presets, inventory freshness and panel placement. Before relying on recording, test five-minute rollover, audio/video, permanent save and cleanup on your own PC.

---
[All pages](README.md) · [Report a bug](https://github.com/Trakstx/bait-and-tackle-ui/issues/new?template=bug.yml)
