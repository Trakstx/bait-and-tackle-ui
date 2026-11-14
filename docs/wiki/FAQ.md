# Frequently asked questions

[Wiki home](README.md) · [Installation](Installation.md) · [Quick reference](Quick-reference.md) · [Troubleshooting](Troubleshooting.md)

## Is loading the skin enough?

No. Native skin XML and external helpers have separate lifecycles. Use Play Bait and Tackle.

## Does every setting need EQ restarted?

No. Ordinary helper settings can change live. Loaded binaries need EQ closed; queued layout/graphics changes wait for a normal exit.

## Does it know my current character?

It follows log activity and observed identity. Check labels after switching and generate fresh lines. Run /who if class/level is uncertain. Snapshots can still be stale.

## Is aggro a percentage against another tank?

No. It is a partial personal melee-hate model.

## Are buff rows the same as EQ slots?

No. The helper controls its own order. Native icons remain available for managing effects.

## Can I move bank items or use live GPS?

No. Bank is an export snapshot; maps show last logged /loc.

## Will recording fill my disk?

Unsaved footage rolls in memory. Saved incidents and the optional OBS runtime consume disk separately. Saved incidents are never automatically deleted.

## Does Stop remove saved footage?

No. It discards unsaved replay and stops recording. Saved files remain.

## Do requests need an email address?

They need a GitHub account. Feedback uses public issues, not a maintainer email form.

## Why is this in docs/wiki instead of the Wiki tab?

The connector cannot write GitHub's separate Wiki repository. These linked, illustrated pages live in the main repository and can be maintained without desktop access.

## Is the project approved by P1999 staff?

No approval claim is made. Review current applicable rules independently.

---
[All pages](README.md) · [Report a bug](https://github.com/Trakstx/bait-and-tackle-ui/issues/new?template=bug.yml)
