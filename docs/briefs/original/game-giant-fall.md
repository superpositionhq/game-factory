# Original brief: giant-fall

The instruction that started this game's building session (2026-10-12), as the coordinator sent it. Machine paths, session ids and tool names are replaced by placeholders; the shared process rules every game session received are in docs/briefs/game-session.md.

Build a GIANT-SLAYER GRAPPLE ACTION game (the user: "an Attack on Titan-like game") in Unreal Engine 5.3, recording its creation as you go. Slug: giant-fall (folder <root>\games\giant-fall, project GiantFall); you choose the final title after the story.

Core: third-person hero with twin grapple lines and a short gas/boost reserve swinging and zipping between buildings, trees and cliffs; giants many times the hero's size roam a walled town or valley; you kill a giant by reaching a weak point (e.g. a glowing seam at the nape/back) and striking with momentum (speed = damage); blades dull and break, resupply at stations; giants grab, swat and stomp with telegraphed attacks; squadmates or townsfolk to rescue. Giants must read as huge (scale, slow heavy animation, footstep dust) and look premium (skeletal meshes from the asset library/Fab, retargeted animation), never primitive shapes.

IP: ORIGINAL only. No Attack on Titan look-alikes: no titans with exposed-muscle anatomy styled like the anime, no "titan" naming, no Survey Corps / wings emblem, no walls called Maria/Rose/Sina, no exact 3D-maneuver-gear design, no characters resembling Eren/Levi/Mikasa. Invent your own world, why the giants come, the hero's gear and factions.

Camera: gentle and readable despite fast traversal (the user gets motion sick): smooth spring-arm follow, no shake, no FOV kicks, no rapid roll; speed shown with wind streaks/particles; a soft lock-on framing for the giant's weak point; the hero stays small in frame.

AutoPlay: bot traverses by grapple, picks a target giant, approaches from behind, hits the weak point, retreats to resupply, plays like a competent human through Enhanced Input injection only. 3 scenarios with deterministic seeds: S1 training yard with one slow giant, S2 town defense with several giants and a rescue, S3 a boss giant (armored or very tall) finale; win/lose is metadata only.

ORDER OF WORK (user's instruction): 1) Background story FIRST: story bible + design doc (premise, world, hero and factions, why the giants come, tone, how the story surfaces in play, core loop, traversal and combat systems, 3 AutoPlay scenarios, art direction with packs, UI style). Then create the repo:
  powershell -ExecutionPolicy Bypass -File <factory>\templates\new-game.ps1 -Slug giant-fall -Path <root>\games\giant-fall -Project GiantFall -Title "<title>" -Description "<one line>"
Put the doc in Docs/design.md, commit it, send it to the coordinator AND Factory ops (for the studio repo/docs/games/giant-fall.md), and wait for the coordinator's OK. 2) Then build: offline code/data/scripts during the hold, engine work only after the coordinator releases the slots. Report each milestone (commit sha) to the coordinator.
