# Atlas VTT integration contract

Source snapshot checked 2026-10-01: `fsafey/atlas-vtt`, commit `cc5d8d281a459b8f602466c918b77cf3855a8c8b`, package version `0.4.2`. This describes inspected source and documented UI, not a live Obsidian acceptance run. Refresh the relevant files for a different version or checkout.

## Source owners

| Concern | Repository source to inspect |
| --- | --- |
| User journey, offline desktop scope | `README.md` |
| Native scene containers and grid fields | `src/app/services/MapPersistence.ts` |
| Loading, rehydration, grid detection | `src/app/services/MapService.ts`, `src/app/MapController.ts` |
| Hex orientation, size and origin | `src/app/grid/hexGeometry.ts`, `src/app/grid/GridSystem.ts` |
| Asset index and collection ownership | `src/app/services/AssetService.ts`, `src/app/services/vault-sync/`, `src/app/utils/dataFileMigration.ts` |
| Presenting a scene | `src/app/services/PlayerWindowPresenter.ts`, `src/app/services/PlayerWindowService.ts` |
| Player-safe frames and pin behavior | `src/app/pixi/`, especially `PinRenderer.ts`; find `withPlayerSafeFrame` |

Do not hard-code the default collection ID. Users can rename collections; Atlas resolves the current default through its asset metadata. Prefer the UI for campaign setup. `.atlas-data` metadata has its own owners and reconciliation logic.

## Native grid hints

| Authoring spec | Atlas field | Meaning |
| --- | --- | --- |
| `square`, `pixels_per_cell` | `type: square`, `size` | Square side length |
| `hex`, `pointy_top`, horizontal hex width W | `type: hex-vertical`, `size: W` | Flat-to-flat width |
| `hex`, `flat_top`, horizontal hex width W | `type: hex-horizontal`, `size: W * sqrt(3) / 2` | Flat-to-flat height |
| `offset_px: [x,y]` | `offsetX`, `offsetY` | Planned origin in unscaled image pixels |
| `render: vtt` | `visible: true` | Atlas draws grid lines |
| `render: baked` or `postprocess` | `visible: false` | Avoid duplicate lines; snapping can remain enabled |
| `type: none`, `render: none` | `enabled: false`, `visible: false`, `snapToGrid: false` | Gridless play |

Hex origin is the top-left corner of cell (0,0)'s bounding box. `grid.size` is not circumradius, stagger pitch or flat-top bounding width. Source coordinates are normalized image space; they are not Atlas world positions. Resizing or transforming the background changes the calibration. Missing hex width means missing `size` in the hints; measure it rather than inventing it.

`enabled`, `visible` and `snapToGrid` are separate persisted fields. The setup plan contains partial field hints and omits appearance preferences such as opacity. It is not a complete `GridState` or a payload to write to disk.

Atlas's distance unit types are `feet`, `yards`, `meters`, `units`; measurement types are `units`, `abstract`. The compiler maps ft -> feet and m -> meters. It converts mi -> feet by 5280 and km -> meters by 1000, preserving the original unit in `source_grid` and flagging the conversion. Abstract uses units with abstract measurement. Null source distance stays unspecified.

## Import and play

1. Render a player-safe background separately and inspect dimensions, geometry and disclosure.
2. Open **Atlas VTT: Open dashboard** in desktop Obsidian. Choose the campaign collection.
3. Import the local image through the asset manager **+**, then create a scene from that map.
4. Set grid type, scale and distance. Align manually against several points across the image. Auto detection can assist an image that already contains a grid; gridless artwork needs chosen calibration.
5. Add labels through text tools or a separately prepared overlay. Add tokens, note links, fog, walls and lights using the corresponding Atlas tools as required.
6. Present the scene in the separate player window, check visible content and fog, and test token movement and distance.
7. Reopen the scene and confirm authored settings and objects persist.

Note pins link Markdown notes or another Atlas map. They are GM preparation aids and are hidden from player presentation. Hex links can anchor notes to hexes, but this package does not assign real cell coordinates or create links. Visible labels require text or a rendered overlay.

The player window presents a selected scene; browsing other GM tabs can hold its current frame. Do not assume the player's image changes just because the GM selected another tab. Inspect the presented scene and content directly.

## Persistence boundary

At the checked commit `ATLAS_SCHEMA` is `atlas-vtt`, `ATLAS_VERSION` is 4. `MapFile` has background, grid, camera and dictionaries of tokens, fog, pins, texts, drawings, walls and lights. Persistence exchanges a Zustand `{state, version}` envelope with a separate scene-state version and performs migrations and path handling.

The authoring `map_spec.version` is a different schema version. A matching JSON shape, top-level schema name or filename extension is not an import test. This package intentionally exports no native scene or vault index. If native export is later requested, inspect the current creation/storage path, produce a new scene in a disposable test vault, and prove load/save/player behavior before claiming compatibility.

## Provenance

Adapted from the user-supplied `/Users/farieds/Downloads/epic-map-forge.zip`; the original archive is unchanged. Inherited map schemas, examples, art guidance, validation and patch machinery were retained. The skill entrypoint, metadata and renderer notes were rewritten; Atlas setup compilation and tests were added. No inherited test report is used as validation evidence.

Original archive SHA-256: `fbdb56fbfbf95ed90fb309db759b33ef332cab41ec41432e5c2c112cbfa9cc90`.
