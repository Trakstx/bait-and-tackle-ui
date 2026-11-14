# Commands and daily checklist

[Wiki home](README.md) · [Installation](Installation.md) · [Quick reference](Quick-reference.md) · [Troubleshooting](Troubleshooting.md)

| Control | Purpose | Prerequisite |
|---|---|---|
| Ctrl+J / Ctrl+H | Shared dashboard in this build | EQ focused; helper running |
| Ctrl+Shift+F9 | Save a recording incident | Rolling buffer active |
| `/log on` | Enable parser input | Run on the character being played |
| `/who` | Supply observed class/level | Message reaches current log |
| `/outputfile inventory` | Refresh bank/equipment snapshot | Repeat after gear/bank changes |
| `/loc` | Update last reported map position | Fresh logged location |
| `/loadskin BAIT_AND_FUCKING_TACLE 1` | Native skin load/reload | Does not replace helper binaries |
| Alt+B / Alt+P / Alt+S | Native buffs / group / spell gems | Your EQ bindings and class may differ |

## Every session

1. Start through Play Bait and Tackle and confirm logging.
2. Check character labels and panel visibility.
3. Run `/who` if identity/class detection is uncertain.
4. Refresh inventory after changing equipment.
5. Test the actual raid CH announcement before relying on the chain.
6. Test-save recording and play the MKV before relying on it as evidence.

After switching characters, generate a fresh logged line. A saved bank/equipment snapshot can remain old even while character detection works.

## What the helper does not know

Server hate tables, unlogged damage, guaranteed unknown buff durations, silent removals, and continuous position are unavailable. Read each feature's status and timestamp.

---
[All pages](README.md) · [Report a bug](https://github.com/Trakstx/bait-and-tackle-ui/issues/new?template=bug.yml)
