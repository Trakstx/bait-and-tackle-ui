Timer integration provenance

Derived from https://github.com/smasherprog/EqTool (MIT, Copyright (c) 2022 Scott).
Required notice: LICENSE-EQTool.txt.

Source references: EQToolShared/Zones.cs; EQTool/Models/BuiltInTriggers.cs;
EQTool/Services/BoatScheduleService.cs; EQTool/Services/Handlers/RingWarHandler.cs;
EQTool/Services/Parsing/RingWarParser.cs; EQToolApis/Controllers/RollTimerController.cs.

Python adapts the timer schedules and log patterns into the BFT helper. It does
not bundle or run EQTool. Shared roll and boat data are read-only GET requests to
the same public PigParse endpoints; no log lines, character names, or locations
are uploaded. Kael pull timers here use locally observed deaths, not EQTool's
SignalR broadcast. Raid timers are estimates from log visibility. Zone-specific
respawns come from the source schedule; unknown zones fall back to 6m40s. Shared
feeds may be stale or unavailable. No timer is proof an NPC is currently spawned.

Speech uses the selected natural Windows SAPI voice, with no pitch effects.
