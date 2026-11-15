# Network and local data

Core log parsing and the settings page run locally. The HTTP listener binds loopback, uses the existing session token and Origin checks for writes, and now limits simultaneous workers, socket read time and total connection lifetime. These limits reduce local resource exhaustion; they do not make an untrusted local account harmless.

Under **Misc â†’ Online features**, opt in separately to shared timer data, item lookups and artwork. They default off. Imported profiles show all normalized setting changes for review and require Save before applying. A failed import preserves unsaved controls and hidden preferences, including recording enablement.

- Shared timers: downloads community timer data from the PigParse API (`pigparse.azurewebsites.net`). Requests expose the ordinary IP address/request metadata to that server.
- Item lookups: retrieves item information using item IDs/names from the Lucy/Allakhazam (`lucy.allakhazam.com`). Cached local results remain usable without enabling new requests.
- Artwork: retrieves item image assets from the Allakhazam (`lucy.allakhazam.com` and `everquest.allakhazam.com`). Cached assets remain usable offline.
- **Check for updates / Download update**: explicit GitHub requests expose ordinary request metadata; downloads use unique staging directories and are hash checked. Downloads are not silently installed.
- **Enable recording**: may download the pinned OBS release from GitHub. Recording is explicit; captures EQ video/process audio, no microphone in the configured scene. Saved incidents stay local in the chosen folder.
- **Feature request / wiki links**: opens an external website in your browser; browser and GitHub/wiki privacy policies apply. No background support upload is added.

Logs, inventory exports, character settings, local sessions, recordings and recovery backups are not uploaded by this hardening work. Shared online sources, browser links and optional downloads are distinct from local parsing. Inspect the source and destination URLs before enabling a service you do not trust.
