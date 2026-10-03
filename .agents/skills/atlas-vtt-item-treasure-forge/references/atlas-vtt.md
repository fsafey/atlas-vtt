# Atlas boundary

Source inspected on 2026-10-02 at commit `9b8acc58a40fed29e412f0770c0a13f1f4147dec` in the Atlas checkout. Refresh relevant source before current compatibility or import guidance; use these findings as orientation.

- `src/app/services/ImageDisplayService.ts:250` exposes `displayImageOnPlayerView(file: TFile)`. It requires an open player window, reads a vault image's binary data, and creates a player-window image overlay. This provides a source-supported presentation path for loot artwork already available as a vault file.
- `src/app/services/ImageDisplayService.ts:283` creates that overlay. `:325` recognizes PNG, JPEG, GIF, BMP, SVG, and WebP extensions. Recognizing SVG does not prove every external SVG feature, font, or inscription will render as intended.
- `src/app/services/AssetService.ts:137` defines the Asset union with token, map, note, statblock, character, scene, encounter, and player types. There is no separate native item/treasure asset type in that inspected union. This skill does not manufacture one or repurpose mechanics records for loot illustrations.

The editable `.item.json` is independent authoring data. Never rename it to `.atlasmap` or insert it into `.atlas-data`. A generated image is not an imported treasure record, inventory entry, token, or playable map object. Map placement belongs to Props & Terrain Forge.

When the user requests Atlas presentation, establish their destination and follow the current supported vault-image workflow. Reading sources or generating artwork does not itself authorize vault mutation. After authorized file placement/presentation, check actual visibility, framing and zoom, inscription legibility, player disclosure, and overlay behavior in the app. File availability and source support do not prove those checks. This authoring package was not accepted in a live Obsidian/player-window session.
