# Maintainer release and documentation workflow

[Wiki home](README.md) · [Installation](Installation.md) · [Quick reference](Quick-reference.md) · [Troubleshooting](Troubleshooting.md)


## Current gate

0.7.0 is a release candidate. Do not describe the recorder as production-verified. Complete a single-instance live EQ recording test before publishing it as dependable evidence capture. The updater checks the latest non-prerelease GitHub release; prereleases do not replace the stable channel.

## Package contract

Publish these exact release assets for version X.Y.Z:

- `Bait-and-Tackle-vX.Y.Z.zip`: complete extracted installer folder, private runtime, manifests, skin, helper, and notices.
- `SHA256SUMS.txt`: SHA-256 followed by two spaces and the exact ZIP filename.
- Optional source archive containing current source, documentation, and third-party notices.

Tag must be `vX.Y.Z`, never blank. The dashboard's `updates.py` VERSION must match the package and release manifest. The updater accepts numeric three-component versions and refuses downgrade installation offers. It checks GitHub's `/releases/latest`, validates asset origins, limits download/expanded size, verifies SHA-256, and rejects extraction paths outside its staging directory. It never installs while the game is running: the staged installer enforces closure and performs backup/verification.

## Before packaging

1. Freeze source and regenerate the payload manifest from release-only files.
2. Run Python compile checks, feature tests, JavaScript syntax checks, and `install.py --verify`.
3. Inspect the archive for personal logs, inventory exports, credentials, settings, localhost session URLs/tokens, backups, videos, caches, absolute developer paths, and test binaries. Exclude all of these.
4. Keep optional OBS binaries out of the initial ZIP; first use downloads the pinned vendor archive and verifies its hash. Include applicable notices for bundled components and derived work.
5. Test a fresh install into a test EQ directory and an upgrade from the previous release. Confirm personal settings, character layouts, and saved incidents survive.
6. Confirm no duplicate helper or OBS process, and that closing EQ stops owned children without killing unrelated applications.
7. Test recorder 5-minute rollover, incident persistence, native hotkey, valid video/audio, and unsupported-device errors. Test update mismatch, network failure, zip traversal, and missing assets.
8. Test UI XML in EQ, including melee/caster layouts, bags, group window and loot window. Do not treat generic XML parsing as sufficient.

## Publish

Create a GitHub Release with the valid tag and honest preview limitations. Attach the package and checksum together before announcing availability. A draft is not available to ordinary update clients. A prerelease is appropriate for testing but is not selected by the current stable update button. Do not publish a new stable manifest pointing at an unavailable asset.

After publishing, check the release JSON anonymously, download the ZIP, recompute SHA-256, inspect extraction, and test the update button from the prior installed version. Retain previous release assets for rollback.

## Rollback

Mark the faulty release clearly and publish a higher patch version containing the fix or rollback payload. Existing clients do not accept numeric downgrades. Preserve backups. Do not force-delete player settings or incidents.

## Feedback triage

Issues are the public intake queue. Feature and bug forms collect structured information without email. Respond and track progress in the issue; close duplicates with a link. Avoid asking users to upload full logs. No GitHub token is embedded in the client, and the app does not post issues on the player's behalf.


## Maintain the illustrated wiki

Canonical pages live under docs/wiki. Update the feature guide and quick reference together. Recheck examples against the actual parser/schema. Render images with isolated fixture data, label them, and inspect every image for private paths/tokens/chat. Verify local links and use a noreply commit identity.

Do not present AI mockups as screenshots of working features. Preserve map/skin credits. Keep release notes and known limitations consistent.

---
[All pages](README.md) · [Report a bug](https://github.com/Trakstx/bait-and-tackle-ui/issues/new?template=bug.yml)
