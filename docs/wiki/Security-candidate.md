# Security candidate: download, test and review

[← Wiki home](README.md)

**Bait & Tackle v0.7.1 security candidate.** This is the test build containing the security remediations, not the older v0.7.0 public preview. The stable release and automatic update download have not been replaced.

## Download the test package

### [Download the security-candidate ZIP](https://github.com/Trakstx/bait-and-tackle-ui/actions/runs/43678729756/artifacts/14147313176)

GitHub requires you to sign in to download Actions artifacts. If that link opens the build page, scroll to **Artifacts** and select **Bait-and-Tackle-security-candidate**. This artifact expires **November 29, 2026**; after expiration a maintainer must generate a new build and update this page.

**33.7 MB downloaded / 61.5 MB extracted.** Optional OBS, recordings and recovery backups need additional storage.

SHA256 of the complete ZIP:

```text
a2966bdbf253097f4f41680004cc3a34907f25faf4d964b49c44cf8857620020
```

## Test it

1. Use a **separate copy of your EQ installation** first. Close EQ before installing.
2. Extract the **entire ZIP** into a normal local folder.
3. Read **SECURITY-CANDIDATE.md** and **RECOVERY.md** in the extracted package.
4. Run **Install Bait and Tackle.cmd**, and select your test EQ folder. Keep the external recovery directory printed by the installer.
5. Launch **Play Bait and Tackle** normally. Helpers should remain standard-user processes. Enable `/log on`, load `/loadskin BAIT_AND_FUCKING_TACLE 1`, and use **Ctrl+J** for settings.
6. Verify your normal panels, saved positions, character switching, hotkeys and refresh. Test recording with real game audio, incident playback, rollover and shutdown. Test normal and administrator-required EQ launch if you use both.
7. Optional online item lookups, artwork and shared timers now require explicit opt-in under **Misc → Online features**.

To restore the recorded installation, close EQ and use **Recover Bait and Tackle.cmd** with its recovery journal. Recovery refuses to overwrite independently modified files; read the conflict before proceeding.

## Give these links to an AI reviewer

- [Full change set and validation summary — PR #1](https://github.com/Trakstx/bait-and-tackle-ui/pull/1)
- [Exact source used for this package](https://github.com/Trakstx/bait-and-tackle-ui/tree/4112dd9647b2fe7b04879c09d815c2a787d8068b)
- [Security findings, implementation and remaining gates](https://github.com/Trakstx/bait-and-tackle-ui/blob/4112dd9647b2fe7b04879c09d815c2a787d8068b/docs/SECURITY-CANDIDATE.md)
- [Recovery design and instructions](https://github.com/Trakstx/bait-and-tackle-ui/blob/4112dd9647b2fe7b04879c09d815c2a787d8068b/docs/RECOVERY.md)
- [Dependency baseline](https://github.com/Trakstx/bait-and-tackle-ui/blob/4112dd9647b2fe7b04879c09d815c2a787d8068b/docs/DEPENDENCIES.md)
- [Network/privacy behavior](https://github.com/Trakstx/bait-and-tackle-ui/blob/4112dd9647b2fe7b04879c09d815c2a787d8068b/docs/NETWORK-PRIVACY.md)
- [Successful Windows build and tests](https://github.com/Trakstx/bait-and-tackle-ui/actions/runs/43678729756)

Suggested review request:

> Review the exact source commit 4112dd9647b2fe7b04879c09d815c2a787d8068b and PR #1 for remaining security defects and behavior regressions. Examine startup/elevation, native path handling, installer recovery, recorder paths/cache integrity, profile imports, HTTP limits and network consent. Distinguish verified issues from hypotheses. Check package receipts against the source and CI evidence. Do not infer P1999 approval or successful live-game tests from automated results.

The package includes `source-commit.json`, `source-package.json`, `native-build.json`, `dependency-inventory.json` and the official Python runtime SPDX for inspection.

## What has been verified

89 Python regressions and the settings.js import-state regression passed. Both Windows CI runs passed. All six native binaries, source/build receipts and 698 payload hashes matched an independent local build from fresh GitHub source. Full dummy-installation recovery preserved unrelated logs and character settings.

**Still pending:** interactive live EQ validation and a separate P1999 permission decision. These results are not independent security certification. [Report test results or defects](https://github.com/Trakstx/bait-and-tackle-ui/issues/new?template=bug.yml); remove private information from logs and screenshots before posting.
