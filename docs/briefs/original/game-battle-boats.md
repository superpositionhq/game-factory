# Original brief: battle-boats

The instruction that started this game's building session (2026-10-12), as the coordinator sent it. Machine paths, session ids and tool names are replaced by placeholders; the shared process rules every game session received are in docs/briefs/game-session.md.

Build a NAVAL BATTLE BOAT game (the user: "a battle boat game") in Unreal Engine 5.3, recording its creation as you go. Slug: battle-boats (folder <root>\games\battle-boats, project BattleBoats); you choose the final title after the story.

Core: third-person command of one warship or gunboat on an open sea/archipelago: steering with throttle and momentum, broadside or turret cannons with arcing shells and lead aiming, torpedoes or mines, armor/hull zones, flooding and fire damage control, repair; enemy ships with formations and AI that flank and kite; upgrades between missions. Water must look premium (UE 5.3 Water plugin or a quality ocean shader from the library/Fab, buoyancy, wakes, spray, splashes), ships from quality packs, never primitive shapes. Must differ from siege-catapult (no static artillery puzzle) and rally-racer (no racing).

IP: ORIGINAL only. No World of Warships / Battleship (board game or film) / Sea of Thieves look-alikes or UI; no real navy insignia; invent your own nations, ships and world (era of your choice: age-of-sail, steam ironclads, or a fictional modern fleet).

Camera: gentle third-person orbit above and behind the ship, stable horizon (never roll the camera with the waves), no shake on firing, a calm zoomed aim view.

AutoPlay: the bot steers, keeps range, leads shots, uses torpedoes and repairs like a competent captain through Enhanced Input injection only. 3 scenarios with deterministic seeds: S1 gunnery training vs targets and one patrol boat, S2 convoy escort vs several raiders, S3 a fleet battle or flagship boss in a storm; win/lose is metadata only.

ORDER OF WORK (user's instruction): 1) Background story FIRST: story bible + design doc (premise, world, nations, the captain and crew, tone, how the story surfaces in play, core loop, ship/weapon/damage systems, 3 AutoPlay scenarios, art direction with packs, UI style). Then create the repo:
  powershell -ExecutionPolicy Bypass -File <factory>\templates\new-game.ps1 -Slug battle-boats -Path <root>\games\battle-boats -Project BattleBoats -Title "<title>" -Description "<one line>"
Put the doc in Docs/design.md, commit it, send it to the coordinator AND Factory ops (for the studio repo/docs/games/battle-boats.md), and wait for the coordinator's OK. 2) Then build: offline code/data/scripts during the hold, engine work only after the coordinator releases the slots. Report each milestone (commit sha) to the coordinator.
