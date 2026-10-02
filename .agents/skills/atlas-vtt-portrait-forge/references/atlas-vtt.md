# Atlas presentation boundary

Local source checked during preparation on 2026-10-02: `/Users/farieds/Project/atlas-vtt`, commit `cc5d8d281a459b8f602466c918b77cf3855a8c8b`. This is source inspection, not an Obsidian acceptance run. Refresh the relevant files before giving current import instructions.

| Concern | Source owner |
| --- | --- |
| Native asset types and image paths | `src/app/services/AssetService.ts` |
| Token portrait display and optional ring | `src/app/packages/components/shared/TokenPortrait.tsx`, `token-portrait.scss` |
| Statblock image selection | `src/app/react/components/FantasyStatblock.tsx` |
| Previewing linked token art | `src/app/services/StatblockDialogService.ts` |

At that snapshot, `TokenAsset.imagePath` supplies token artwork. The asset union has no standalone portrait type. A `character` asset with opaque JSON does not establish a portrait import API. Framed token portraits use a circular crop; unframed images use containment. Statblock portraits are derived from linked token artwork.

Portrait Forge therefore delivers ordinary illustration files, editable source, and review evidence. Reusing a portrait in an Obsidian note or translating it into a native Atlas token requires the requested separate workflow. Do not register it as a guessed native portrait asset, rename authoring JSON to `.atlasmap`, write `.atlas-data` indexes, or imply that generating the image connected it to a statblock.

If the user requests import, locate the current checkout and intended vault/collection, inspect the current source and UI journey, and follow the requested asset workflow. Keep an untouched portrait master before any tabletop crop. Respect the user's browser-selection instructions for browser work. Vault changes and image rendering have separate authorization scopes.

Report native import only after it happened. Report presentation verification only after seeing the intended artwork in its consuming UI and, where relevant, the player window. Portrait authoring does not require grid calibration, walls, lighting, fog, or token-distance tests.
