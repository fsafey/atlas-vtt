# Atlas token boundary

Source inspected on 2026-10-02 at `9b8acc58a40fed29e412f0770c0a13f1f4147dec` in the active Atlas worktree. These findings establish source behavior, not Obsidian acceptance. Resolve paths from the current Atlas checkout and reread them for a later compatibility claim.

| Source path | Observed behavior and implication |
| --- | --- |
| `src/app/services/AssetService.ts`, `TokenAsset` | Artwork is `imagePath`; `showRing` defaults to framed unless false. `size` is a grid footprint multiplier, independent of image pixel dimensions. Forge asset IDs are authoring IDs, not native Atlas IDs. |
| `src/app/pixi/token-renderer/tokenArtwork.ts` | Framed artwork is circularly masked and sized square. Unframed artwork removes that mask and fits proportionally by the longest image edge. Use whole transparent art with the ring off for cutouts and top-down pieces. |
| `src/app/packages/components/shared/TokenPortrait.tsx` and `token-portrait.scss` | UI previews apply an optional ring and circular crop with a 5 percent inset; unframed previews contain the whole artwork. The prompt's ordinary margin is not a guarantee of surviving this crop. |
| `src/app/packages/components/asset-manager/token-creator/tokenImages.ts` | Framed uploads use the creator's crop placement; unframed tokens use the full image. Framed conversion uses a 256 pixel minimum and the token preset's maximum. |
| `src/app/imageProcessing/imageProcessing.ts`, `IMAGE_PRESETS.token` | Token import conversion fits within 400 by 400 pixels at WebP quality 0.85. Preserve the higher resolution source separately and inspect the converted import for small-size readability and alpha if import is later requested. This preset is source-specific, not a generation limit. |
| `src/app/packages/components/asset-manager/token-creator/saveTokenPreviews.ts` | Saving new tokens writes images then registers assets with `showRing`; editing can replace existing artwork. Forge authoring does not execute this writer. |
| `src/app/pixi/token-renderer/tokenSizing.ts` | Token size and UI scale derive from grid and token multipliers. Screen appearance also depends on map zoom. Requested review sizes are useful checks, not a native size binding. |

The filtered brief's `atlas_display_hint.showRing` is a recommendation derived from border policy, not an import instruction or performed mutation. For `atlas_ring` it is true; for `baked` or `none` it is false. Avoid a second Atlas ring around an already baked border unless the user specifically requests that treatment.

When import is requested in a separate authorized workflow, refresh the creator UI/source and select the intended crop/ring. Check the resulting stored artwork, token placement, rotation, size, readability over the intended map, player presentation/disclosure, and save/reopen persistence as relevant. Report which of those were observed. No token specification or image brief is native Atlas metadata or a `.atlasmap` scene; do not rename it as one.
