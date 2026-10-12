# __TITLE__

__DESCRIPTION__

![__TITLE__](Docs/screenshots/hero.jpg)

<!-- Hero image + captioned gallery from Docs/screenshots/ (jpg, in LFS), taken from stills of validated gameplay
     recordings. Replace this comment with the gallery once the first recording is in. -->

## Play

- Engine: Unreal Engine 5.3 (Windows, DirectX 12).
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
