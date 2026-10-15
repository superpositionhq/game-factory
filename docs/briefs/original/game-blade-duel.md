# Original brief: blade-duel

The instruction that started this game's building session (2026-10-12), as the coordinator sent it. Machine paths, session ids and tool names are replaced by placeholders; the shared process rules every game session received are in docs/briefs/game-session.md.

Build a BLADE DUEL FIGHTING game (the user: "a blade fighting game") in Unreal Engine 5.3, recording its creation as you go. Slug: blade-duel (folder <root>\games\blade-duel, project BladeDuel); you choose the final title after the story.

Core: one-on-one 3D weapon duels in arenas: a roster of at least 4 original fighters with different blades (katana, longsword, twin sabres, glaive or similar) and movesets; light/heavy attacks, directional guard, parry with a tight window, dodge/sidestep, stamina or posture meter, counters and a finisher; best-of-3 rounds; modes: story/arcade ladder vs CPU, and local 2-player versus on one PC (two gamepads or split keyboard, shared camera). Character models and animation must be premium (Fab/animation packs, retargeted sword animation sets), hit reactions, weapon trails, sparks on clash, never primitive shapes. Must differ from liaozhai-night (no 2.5D exploration or monster hordes: this is a versus duel fighter).

IP: ORIGINAL only. No Soulcalibur / Samurai Shodown / For Honor / Bushido Blade characters, moves, UI or announcer look-alikes; invent your own world, fighters and why they duel.

Camera: classic versus side camera that keeps both fighters in frame, gentle zoom with distance, no shake on hits (use hit-stop and sparks instead), no FOV kicks.

AutoPlay: in recordings both fighters are bots (P1 via Enhanced Input injection logged with player index, P2 as CPU or a second injected player), playing like competent humans: spacing, guarding, punishing, parrying sometimes. 3 scenarios with deterministic seeds: S1 first ladder duel (tutorial-level opponent), S2 a mid-ladder duel in a different arena, S3 the final boss duel or a 2-player versus match; win/lose is metadata only.

ORDER OF WORK (user's instruction): 1) Background story FIRST: story bible + design doc (premise, world, the fighters and why they duel, tone, how the story surfaces in play: pre-fight lines as subtitles, ladder endings; core combat systems and frame data approach; roster; arenas; 3 AutoPlay scenarios; art direction with packs; UI style). Then create the repo:
  powershell -ExecutionPolicy Bypass -File <factory>\templates\new-game.ps1 -Slug blade-duel -Path <root>\games\blade-duel -Project BladeDuel -Title "<title>" -Description "<one line>"
Put the doc in Docs/design.md, commit it, send it to the coordinator AND Factory ops (for the studio repo/docs/games/blade-duel.md), and wait for the coordinator's OK. 2) Then build: offline code/data/scripts during the hold, engine work only after the coordinator releases the slots. Report each milestone (commit sha) to the coordinator.
