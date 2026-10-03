# Atlas boundary and source snapshot

Source refreshed on 2026-10-02 in `/Users/farieds/Project/atlas-vtt-image-forges` at commit `9b8acc58a40fed29e412f0770c0a13f1f4147dec`. This is source evidence, not an Obsidian import or tabletop acceptance run. Locate the active checkout and reread these files before making current compatibility claims:

| Concern | Source |
| --- | --- |
| Asset union, image path, optional frame | `src/app/services/AssetService.ts` |
| Unframed artwork containment and aspect ratio | `src/app/pixi/token-renderer/tokenArtwork.ts` |
| Token sizing convention | `src/app/pixi/token-renderer/tokenSizing.ts` |
| Rotation, size, and layer fields | `src/app/types.ts`, `src/app/pixi/TokenRenderer.ts` |
| Native image spawning | `src/app/packages/components/asset-manager/utils/tokenSpawnService.ts` |

At this snapshot, the asset union has no dedicated prop or terrain type. `TokenAsset.imagePath` stores token artwork; `showRing: false` removes the frame mask and fits the complete image proportionally by its long edge. Native token sizing follows the token multiplier convention, not arbitrary world width and length. `BaseToken` includes rotation and layer fields, but no custom artwork anchor. These observations make an unframed image a candidate placement path; they do not establish a complete prop import workflow or alpha correctness in the app.

The forge's footprint, margin, and normalized anchor are authoring requirements. Do not map them to guessed native fields, silently promise rectangular occupancy, write `.atlas-data` indexes, or call this JSON a scene export. Baked shadows rotate with artwork. Custom anchors and physically correct lighting need observed placement or additional work in the consuming workflow.

If import is requested, establish the intended vault and asset collection, use the current supported image workflow, and inspect the consuming scene. Verify visible scale against the destination grid, orientation, anchor behavior, layering, alpha edges against the actual map, and player display. Check save/reopen persistence and required interaction before tabletop acceptance. Record image creation, import, placement, and acceptance separately. Honor the user's browser selection rules if browser work becomes necessary.
