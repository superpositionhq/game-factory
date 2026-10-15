# Original brief: rts-command

The instruction that started this game's building session (2026-10-12), as the coordinator sent it. Machine paths, session ids and tool names are replaced by placeholders; the shared process rules every game session received are in docs/briefs/game-session.md.

Build a REAL-TIME STRATEGY game in Unreal Engine 5.3, recording its creation as you go. Slug: rts-command (folder <root>\games\rts-command, project RtsCommand); you choose the final title after the story.

Genre requirements: top-down/three-quarter RTS camera (pan/zoom, gentle, no rotation jerks), base building (at least HQ + 2 production buildings), resource gathering by worker units, 3+ unit types with counters, box selection and right-click orders, fog of war or at least a revealed-area mechanic, an enemy AI that builds and attacks. Keep scope small and polished: one faction vs one AI faction is fine. Must not duplicate tower-defense or siege-catapult (no lane defense, no catapult physics as the core).

Start with the background story and design doc (see ORDER OF WORK): an original world and conflict, how the story surfaces in play (mission objectives, environmental storytelling, unit barks as subtitles), 3 AutoPlay scenarios (e.g. tutorial skirmish, defend-and-expand, destroy the enemy HQ) with deterministic seeds, the art packs you'd use from the asset library (or the packs to request), and the UI style. Send it to the coordinator and Factory ops, wait for the OK, then build. The AutoPlay bot must play like a competent human (build order, gather, expand, attack) so the recordings are watchable.
