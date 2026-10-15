# __TITLE__

__DESCRIPTION__

<!-- PLACEHOLDER, replace before the game is content-complete: 5-7 real gameplay stills in Docs/screenshots/ (jpg,
     in Git LFS, from validated recordings or the framing-gate screenshots), shown here as a hero image plus a
     captioned gallery, e.g.
       ![<title>](Docs/screenshots/hero.jpg)
       | ![](Docs/screenshots/<name>.jpg) | ![](Docs/screenshots/<name>.jpg) |
       |---|---|
       | <what it shows> | <what it shows> |
     Link only files that are committed, and check on github.com that every image renders. -->

## Play

- Engine: Unreal Engine 5.7 (Windows, DirectX 12).
- Open `__PROJECT__.uproject`, or run the packaged `__PROJECT__.exe` from a release build.
- Controls: _fill in_.

## Scenarios

| # | Name | Start state | Win / lose |
|---|---|---|---|
| 1 | _fill in_ | | |

## Project layout

| Path | What |
|---|---|
| `Source/__PROJECT__/` | gameplay C++ (`AutoPlay/` = the scripted-play subsystem used for recordings) |
| `Content/` | maps, Blueprints, data assets, imported packs (`Content/Fab/<Pack>/`) |
| `Scripts/` | every editor Python script that was run to build the content, kept unchanged |
| `workflow.jsonl` | one row per editor/code operation, written as it happened |
| `assets.manifest.json`, `Docs/ThirdPartyNotices.md` | third-party assets: source, licence, files used, changes |
| `Dataset/` | the built dataset (gameplay videos, screenshots, replay scripts) |
