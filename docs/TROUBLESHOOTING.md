# Troubleshooting

## Nothing appears

1. Confirm EQ is running through Play Bait and Tackle, not only through eqgame.exe.
2. Use windowed/borderless mode and enable `/log on`.
3. Press Ctrl+J while EQ has focus. Check the feature's Show/Enabled setting.
4. If a newly installed helper has not loaded, close EQ normally and restart through the launcher. An XML reload alone cannot replace a loaded graphics component.
5. An error saying “Open one EverQuest session from this installation” means the refresh tool did not find the expected EQ session. Do not repeatedly launch additional helpers.

## UI falls back to default / XML error

Copy the exact Source and error text from EQ's chat. Restore the last working skin files or reinstall a verified release with EQ closed. A valid XML parser check is necessary but does not prove compatibility with EQ's UI schema. Do not add controls from another client version without live validation.

## Bags overlap or items cannot be clicked

Native container windows can reserve invisible client-controlled space. Repositioning only visible slots does not remove that hit region. Avoid overlapping bag window rectangles. The current vertical arrangement puts C/X controls at the top. Do not assume XML can expose nonexistent slots safely or dynamically rewrite native container capacity.

## DPS / buffs / chain does not update

Check fresh log lines for the active character. Ensure the relevant messages are enabled in EQ. Test a known chain call or rule. Review ambiguity markers and duration overrides. Wrong or absent messages cannot be repaired by a more precise-looking timer.

## Recorder unavailable or no saved clip

Check Recorder status, write access to the chosen folder, free space, OBS first-download completion, and graphics driver support. Save only after the buffer becomes active. Wait for the saved filename. Open the resulting MKV and confirm both picture and sound. Windows may restrict process-audio capture on unsupported builds. Do not enable microphone or display capture as an unnoticed fallback. The preview's final end-to-end test is pending.

## Update check fails

GitHub may be unavailable or rate limited. Retry later. A release missing the expected ZIP/checksum is not installable through the button. Never bypass checksum failure. Download from the official Releases page if needed and verify its published checksum. An update is staged, not silently installed; close EQ and run the extracted installer.

## Reporting

Use the GitHub bug form. Include version, Windows version, resolution, the feature affected, exact error, and minimal reproduction steps. Redact character/chat details as needed. Never post credentials, complete logs, or dashboard URLs.
