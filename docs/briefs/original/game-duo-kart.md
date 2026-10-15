# Original brief: duo-kart

The instruction that started this game's building session (2026-10-12), as the coordinator sent it. Machine paths, session ids and tool names are replaced by placeholders; the shared process rules every game session received are in docs/briefs/game-session.md.

Build a LOCAL 2-PLAYER ARCADE KART RACER (the user: "a Mario Kart-like local game where 2 players can play against each other locally") in Unreal Engine 5.3, recording its creation as you go. Slug: duo-kart (folder <root>\games\duo-kart, project DuoKart); you choose the final title after the story.

Core: two human players on one PC in split-screen (horizontal or vertical split, choose and justify), each with a gamepad or one half of the keyboard (WASD+keys / arrows+keys), device assignment screen; arcade kart handling (drift with charge-up boost, jump/hop, item pick-ups and a small set of original items with fair counterplay, rubber-banding kept subtle); CPU racers fill the grid (e.g. 6) so races feel lively; several original tracks with distinct themes, shortcuts and hazards; race modes: Grand Prix cup (points over tracks), single Versus race, and optionally a battle/arena mode if time allows. Must clearly differ from rally-racer (no realism, no off-road rally, no co-driver; cartoonish arcade, items, split-screen).

IP: ORIGINAL only. No Nintendo characters, item designs (no ? boxes, no shells/banana look-alikes, no blue-shell analogue), track names or signature tracks (no Rainbow Road copy), logos, UI or sound look-alikes. Invent your own world, drivers and items.

Camera: gentle chase cam per player, no shake, no FOV kicks on boost (use speed lines/particles instead), stable horizon; karts readable in each half of the split screen.

AutoPlay: the contract drives the whole local match. For recordings both human slots are played by bots through Enhanced Input injection per local player (log the player index in inputs.jsonl), skill-scaled, playing like competent humans (racing lines, drifting, using items sensibly). The recording is the full split-screen frame. Define 3 scenarios with deterministic seeds: S1 a 2-player versus race on the first track, S2 a mid cup race with items and CPU racers, S3 a final track or battle round; win/lose/finish order is metadata only.

ORDER OF WORK (user's instruction): 1) Background story FIRST. Before any project or code, write the story bible + game design doc (premise, world, drivers and why they race, tone, how the story surfaces in play: track intros, rival banter as subtitles, cup endings; core loop; split-screen and input plan; items; tracks; 3 AutoPlay scenarios; art direction with the packs you'd use from the asset library or packs to request; UI style). Then create the repo:
  powershell -ExecutionPolicy Bypass -File <factory>\templates\new-game.ps1 -Slug duo-kart -Path <root>\games\duo-kart -Project DuoKart -Title "<title>" -Description "<one line>"
(this only creates files and the GitHub repo, no engine run, so it is allowed during the hold). Put the doc in Docs/design.md, commit it, and send it to the coordinator AND to Factory ops (for the studio repo/docs/games/duo-kart.md). Wait for the coordinator's OK on the story/design. 2) Then build: offline C++/data/scripts while the hold lasts, engine work only after the coordinator releases the slots. Report each milestone (commit sha) to the coordinator.
