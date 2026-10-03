# Carrier adaptation and visual review

Keep the same emblem geometry recognizable across carriers. Meaning lives in the motif count, silhouette, arrangement, color roles, and distinctive marks. Material treatment is allowed to change how those features are rendered.

| Carrier | Useful adaptation | Check in the returned image |
| --- | --- | --- |
| Emblem, sigil, or insignia | Strong outline, balanced negative space, limited major forms | Readable at its intended small size; no invented marks or letter-like noise |
| Coat of arms | Shield/frame composition or requested fantasy form | Main device remains dominant; optional ornament does not obscure it |
| Wax or embossed seal | Raised/recessed relief with one material color | Device remains clear under shading; relief does not create extra motifs |
| Banner or flag | Cloth proportions, attachment side, gentle folds, edge treatment | Device orientation and count match base; folds do not erase key geometry |

Palette roles describe identity, not an obligation to paint metal or wax in three colors. For a monochrome seal, preserve motif and arrangement through relief while recording the intentional material constraint. Keep the original palette in the shared identity for other carriers. If mirroring a flag reverse side is requested, record that explicit exception; do not silently flip the emblem on the primary face.

Inspect the anchor at full size and at the requested `reading_size_px`. A motif that collapses to texture at that size needs a deliberate simplified variant or a revised reading-size requirement. Preserve user-chosen details until that conflict is resolved. Do not turn a small-size review into an unsolicited historical-heraldry audit.

For a transparent emblem, inspect actual alpha, outer edge halos, and crop margins. For a cloth carrier, verify complete fabric edges and expected background rather than assuming every flag is a cutout. A PNG extension and checkerboard painting are not transparency evidence.

## Exact lettering

Record the exact supplied or delegated wording in the source. Do not normalize apostrophes, punctuation, capitalization, or line breaks without a requested change. Exact lettering can be composed deterministically after generating the image, using the reserved text area and the user's chosen type treatment. Export and view the final composed asset to catch clipping or missing fonts. The helper prepares that plan; it does not compose typography.

For `raster_verify`, compare every character against the source and inspect the reading size. A failed word is a mismatch, even when the surrounding image is good. For `compose_later`, keep wording out of the generation prompt so the renderer creates the requested blank area; share the wording separately with the composition tool. Do not deliver the blank image as a completed lettered design.

## Minimal render record

Keep the source ID/revision, asset ID, final local file, actual width/height, observed alpha where relevant, base-reference file, motif/arrangement/palette comparison, small-size findings, exact-text result, and remaining mismatches. Record what was viewed rather than checking every box by assumption. Generated, visually reviewed, user-approved, imported, and player-window-verified remain separate states.
