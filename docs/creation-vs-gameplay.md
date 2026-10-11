# Creation data vs Lab gameplay data

Superposition Lab's `game_recording` type (upload contract schemas 3–5, `docs/planning/upload-contract-v2.md`
in `superpositionhq/superposition-training`) records people **playing** existing games. The packages here record
games being **made**. Both involve 3D games; the difference is the task, not the dimension.

| | Vendor packages (parkour, island_explore) | LiaoZhai packages (this repo) | Lab gameplay (`game_recording`) |
|---|---|---|---|
| Task | building a UE game | building features of a shipped Unity game | playing a game |
| Actions | semantic editor ops (`set property X on actor Y`) | editor-level ops derived from real commits | raw `key_down`, `mouse_move`, `cursor_state` with ns QPC timestamps |
| Who acted | script; order reconstructed | real developers (anonymized) | a real contractor |
| Timing | none | commit time per step | nanoseconds per event |
| Speech / reasoning | written reason per step (often reconstructed) | commit message | microphone narration + transcripts |
| Video | 4K editor screen at 15 fps; 1–2 min playtest without inputs | none yet | game at native resolution, 60 fps, plus system and mic audio |
| Ground truth | finished project, code diffs, rebuildable | project at the end commit, real history | pixels and inputs only |
| Length | one small game | one feature (e.g. 27 commits / 811 steps) | ≥ 7-minute sessions |

Lab bundle (schema 3): `video.mkv` (H.264, native resolution, 60 fps, no audio), `system_audio.mka`,
`microphone.mka`, `inputs.jsonl`, `metadata.json` (clock samples, `video_start_offset_ns`), `manifest.json`
(sha256). Schema 5 adds `cursor_state`, `focus_lost/gained`, `cursor_mapping`, `input_quality`.

None of the vendor packages fit Lab gameplay datasets: no input logs, no voice, 1–2 minutes of play, editor
chrome around the viewport. They are closer to creative-tool / computer-use trajectories (like the Lab's
planned `blender_coa` chain-of-actions type).
