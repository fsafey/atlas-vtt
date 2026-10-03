# Atlas presentation boundary

Source inspected in `/Users/farieds/Project/atlas-vtt-image-forges` at commit `9b8acc58a40fed29e412f0770c0a13f1f4147dec` on 2026-10-02. Refresh these paths in the active Atlas checkout before claiming current compatibility. This is source evidence, not observed in-app acceptance.

- `src/app/services/ImageDisplayService.ts`: `displayImageOnPlayerView` reads a vault image, requires an open player window, creates a blob URL, and displays an image overlay in that window. Image context menus expose `Display on player view`.
- `src/app/plugin/registerCommands.ts`: the active image command `display-image-on-player-view` and matching dismissal command route to that service.
- `src/app/services/AssetService.ts`: the `Asset` union contains token, map, note, statblock, character, scene, encounter, and player assets. There is no distinct heraldry, symbol, seal, banner, or flag asset type in this snapshot.

An exported heraldry image can be a vault image presented through the image overlay when the user requests that workflow. Do not invent a heraldry asset registration or treat the source JSON as native Atlas data. A map-placed banner goes to Props & Terrain Forge; a sealed document goes to Handout Forge.

The skill creates artwork and presentation hints. It does not mutate a vault, write `.atlas-data`, produce `.atlasmap`, or verify a player window. Actual import/display needs its own user-requested action and live image/player-window inspection. GM-only information baked into pixels cannot be removed by a source visibility flag.
