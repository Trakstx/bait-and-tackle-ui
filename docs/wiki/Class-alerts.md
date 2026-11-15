# Class-aware alerts and custom triggers

[Wiki home](README.md) Â· [Installation](Installation.md) Â· [Quick reference](Quick-reference.md) Â· [Troubleshooting](Troubleshooting.md)

Class alerts use observed identity or a manual class override. Enable only the presets you want. Custom rules support literal text and wildcard matching, class restrictions, severity, short messages, estimated countdowns, and Windows speech. They do not execute game commands. Test each rule with a representative message. Audio uses the selected installed Windows voice. Avoid putting credentials into trigger text or shared profiles.



## Class awareness

Run `/who`, inspect the detected character/class, and use a per-character override if needed. Review eligible presets before enabling audio. Examples include enrage, gating, invis fading, death, fizzles, resists, charm breaks, failed feign death, interrupted songs and failed hide. They still require matching log lines.

## Custom rule example

| Field | Example |
|---|---|
| Name | Casting reminder |
| Match mode | Exact |
| Match text | `Your spell fizzles!` |
| Alert message | `CAST FAILED â€” {character}` |
| Severity | Warning |
| Countdown | 0 for a short banner |
| Classes | Cleric |

Wildcards use `*` and `?`, not executable code. Message substitutions include `{character}`, `{class}` and `{line}`. Keep rules narrow and apply cooldowns where repeated lines would be distracting.

## Audio test

Choose an installed Windows voice, speed and volume, then use Test voice. Speech is local. A successful voice test confirms output, not the rule's match. Test the rule separately against representative text.

![Screenshot: Class-aware alerts and custom triggers](images/triggers.png)

*Real v0.7.0 dashboard rendered with isolated sample data. This screenshot documents controls and appearance, not successful live gameplay.*


---
[All pages](README.md) Â· [Report a bug](https://github.com/Trakstx/bait-and-tackle-ui/issues/new?template=bug.yml)

## Self-invulnerability timers (next candidate)

Class Alerts tracks self landings for Divine Aura/clickies on every class, Divine Barrier, Harmshield, Quivering Veil of Xarn and Kazumi's Note of Preservation. It does not start an active-effect timer merely because casting began or a spell was memorized.

An estimated 18-second active countdown appears ahead of other alerts, with a three-second ending notification when speech is enabled. DA is conservatively timed at 18 seconds because the wiki lists 18–24 seconds. A timer reaching zero says to check the buff; an observed fade is the authoritative clearing event. Zoning marks active observations uncertain. Shared bard-protection landing text is marked `?`; a recently observed Armor of Protection cast suppresses that ambiguous match.

In Class Alerts, choose Divine Aura source for the current character: Automatic (duration only; reuse unknown), Spell gem (estimate 15-minute reuse), or Clicky (no guessed reuse/charges). Barrier uses its 15-minute spell reuse; Harmshield/Veil use 10 minutes. Bard reuse is estimated at three minutes only when the player's named cast and landing are both observed; receiving another bard's DA does not start your own reuse. These are estimates, not server readiness checks.

References: [Divine Aura](https://wiki.project1999.com/Divine_Aura), [Divine Barrier](https://wiki.project1999.com/Divine_Barrier), [Harmshield](https://wiki.project1999.com/Harmshield), [Veil of Xarn](https://wiki.project1999.com/Quivering_Veil_of_Xarn), [Kazumi's Note](https://wiki.project1999.com/Kazumi%27s_Note_of_Preservation).
