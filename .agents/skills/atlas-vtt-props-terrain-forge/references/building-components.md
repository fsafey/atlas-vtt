# Reusable building components

Use for a standalone exterior, roof, ruin section or similar piece intended for a composed map. Map Forge owns plot geometry, neighborhood layout, entrances/access, terrain and sprint coordination. This forge owns the piece and its reusable image contract. A request for one tree or table stays on the ordinary prop path.

## Bind the piece to its destination

Read the supplied plot/card and exact layout revision. Preserve its stable slot/entity ID in the handoff; keep it outside `props_spec` if the schema has no field for it. Resolve the camera/projection, compass orientation, palette/materials, light direction, scale convention and intended display size from the destination. Reuse these across the set. If the source is incomplete, draft the piece with stated assumptions and leave dependent placement unresolved.

Use existing `object_id` for the reusable identity and separate `asset_id` values for variants. Record expected connected roof wings, courtyard voids, public exterior signature and entrance-facing features in supported description/reference fields. Do not create a playable floorplan or invent private interiors to make a roof interesting. Render individual files so accepted pieces can be reused independently.

Keep three different outlines explicit:

| Outline | Meaning |
| --- | --- |
| Ground footprint | Geographic/local plot geometry supplied by Map Forge. `footprint` gives world-unit dimensions, not projected roof size or a collision polygon. Preserve voids and entrances in the layout source. |
| Pictorial silhouette | Roof overhangs, facade projection, perspective and any agreed visual enlargement for readability. It can exceed the ground footprint without moving the ground anchor. |
| Alpha bounds | Measured nonzero-alpha pixels, including shadows and fragments. Useful for cropping/padding checks, never a substitute for either outline above. |

Reuse `composition.anchor` as the requested full-canvas normalized anchor with upper-left origin. Record what it represents, such as the center of the ground footprint, and verify that contact point in the actual image. Padding, a projecting facade or a shadow can move the visible center. Do not anchor from the roof centroid by default. If the source anchor or ground footprint cannot be located reliably in a pictorial render, report uncertainty instead of manufacturing precise placement.

## Generate and review a component

Use the available `imagegen` workflow when rendering or editing is requested. Supply the actual inspected references and narrow target. A sketch, plot mask or reference board is guidance, not a guaranteed constraint. If exact roof/court geometry is critical, hand off to an authorized deterministic drawing/rendering workflow for that geometry; do not promise model precision or introduce a new renderer as part of ordinary skill use.

Inspect each actual candidate before selecting it for a set. Check the connected mass and openings, required signature, camera, material scale and shadow against the destination. Compare at its intended placed size as well as full size. A correct color or nearby work prop does not compensate for the wrong roof family. Preserve courtyard transparency when it should reveal the destination; a deliberately baked courtyard surface must be recorded as part of the asset.

Measure dimensions, alpha occupancy and all four margins with the existing `inspect-image` helper. Inspect light/dark backdrops and internal gaps visually. Include the complete shadow in the allowed padding and proposed change region. Verify the observed anchor against the requested anchor after generation or trimming; any later crop requires new dimensions, anchor coordinates and image hash. Never trim or overwrite approved originals silently.

In a set, compare candidates together with an accepted style reference at the intended display sizes. Keep roofs, walls, vegetation and small props at compatible scales. Cast shadows and low-oblique facades constrain rotation; a transform can be mathematically exact yet visually wrong. Coordinate any rotation/light conflict with Map Forge before assembly.

## Component handoff

Use the map-owned production layout template linked from `SKILL.md` when an assembly handoff is needed. It is a separate, optional JSON convention, not an extension of `props_spec` and not an automatically validated format. Map Forge maintains slot geometry and placement; supply the component section and link the existing review record for detailed findings.

Provide the props source path, spec/object/asset IDs, revision and hash; versioned actual file path, measured dimensions and file-byte hash; requested and observed anchor, alpha bounds and padding; camera/scale/light/shadow constraints; inspected reference paths; and visual evidence. Let Map Forge choose the board transform from the recorded ground and raster anchors. An ungenerated candidate has no actual file/dimensions/hash; keep those null.

Keep `proposed`, `reviewed`, selected-for-production `accepted` and `user_approved` distinct. Record who selected a component, under what authority and for which use; an agent's quality review cannot set user approval. Preserve accepted files and make narrow replacement versions. Selection for a library does not establish final composition quality, native placement or tabletop acceptance.

For revisions, compare shape, anchor, padding and shadow with the accepted base, then report the changed extent and any drift to Map Forge so it can recheck affected neighbors and conserved regions. Source validation, alpha measurements, visual inspection, assembly and native acceptance remain separate claims.
