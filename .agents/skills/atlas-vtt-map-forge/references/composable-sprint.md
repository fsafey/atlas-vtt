# Composable map production sprint

Use this mode for dense keyed maps, or when the user requests an editable coordinate board, pinned references or reusable pieces. The useful unit of iteration is a representative neighborhood. A small map or isolated prop does not need a sprint ledger. Adapt to the existing editor and project files; this skill does not supply a board application, renderer or native scene exporter.

## Fix the source and working frame

Record the exact layout revision and source file hash before generating components. Keep stable entity/plot IDs, district membership, ground polygons including voids, entrances, access paths and terrain. Use the project's existing source if it is already authoritative; do not force a campaign-specific layout into `map_spec`. Record its format and owner. Where `map_spec` is the source, preserve its supported geometry rather than adding polygon or pin keys to its schema.

Make the production board editable: plot outlines, IDs and reference cards remain separate objects/layers. Save those objects in the existing editor or an editable coordinate document, with a sidecar join from each card to its source plot ID. A flattened reference sheet alone is not an editable board. Freeze a source snapshot for each pilot; a deliberate layout revision produces a new snapshot and invalidates affected placements.

Distinguish three spaces:

| Space | Contract |
| --- | --- |
| Ground | Geographic/local coordinates, explicit units, origin, axes and CRS when applicable. Owns physical footprints, entrances and anchors. |
| Production board | Explicit canvas/frame dimensions and ground-to-board transform. Grid cells organize authoring and review; they do not set game distance. |
| Asset raster | Measured image dimensions, pixel origin and anchor. Roof/facade projection, overhang, padding and shadow can extend beyond the ground footprint. |

Retain `gameplay.grid` separately for Atlas calibration. Source bounds and pins are placement targets. Neither a grid overlay nor a low-oblique painting proves geographic registration. Record any pictorial enlargement and projected displacement without changing ground geometry. If the ground-to-picture mapping is uncertain, leave that alignment unresolved rather than inventing a transform from nearby roofs.

## Pin references to plots

Each card joins a stable slot/entity ID to its source geometry and records:

- Expected architecture: roof family, connected wings, courtyard openings, entrance direction, and the coarse signature that must read at the intended zoom.
- Actual inspected reference path, role, traits to use/ignore and inspection state. Use existing owner-specific reference roles; the card adds placement context, not a new renderer control.
- Candidate asset ID/version, actual available file, review findings and disposition. Keep user approval with its evidence; a reviewer cannot grant it.

Pin by source ID and explicit coordinates, never by a visual guess at a similar district. Keep cards outside clean player art. The production sidecar and working board are private masters by default: reference cards and source provenance can carry GM information. Give each card its own `visibility` (`public` or `gm_only`); a public slot does not make its cards public. Derive a separate public board manually by selecting only reviewed player-safe slots, cards, images and prose, and removing private provenance and links. Inspect that entire derivative before sharing; no automated sidecar filtering is provided. Only player-safe references and exterior instructions reach a player image brief.

## Pilot, then expand

Choose a small contiguous neighborhood that exercises the difficult cases: similar roof types, an open court, a narrow access lane, slope or vegetation overlap as relevant. Explain the selection; do not impose a universal count. Define the intended overview and close-up display sizes before rendering. A detailed signature that disappears at overview size needs a coarser silhouette or a separate detail view.

Coordinate a shared camera/projection, material palette, light direction, scale convention, edge treatment and shadow policy. Route reusable exteriors/roofs and other pieces to Props & Terrain Forge, which uses the available image workflow when rendering is requested. Keep playable floorplans with Map Forge. For exact geometry, use an authorized deterministic drawing/rendering workflow for the shape and an image workflow for creative treatment where useful. Reference boards, sketches and masks guide a model; they do not lock its pixels.

Review the actual pilot candidates and their arrangement before expanding. Preserve the selected versions and recorded reasons. Proceed with reversible authoring already authorized by the user; do not add a confirmation round for every card. If the user reserved selection/approval, keep it pending. A failed pilot calls for a focused change in shape, reference, framing or scale before multiplying assets.

## Hand off deterministic assembly

Use `templates/production-layout.template.json` as an optional sidecar convention. It is not a `map_spec`, `props_spec`, compiler input or validated native format. The template is intentionally incomplete: null paths, hashes, measurements and approvals are unknown, not defaults or evidence. Fill only observed values. Existing source compilers do not validate this sidecar; check its joins, frames and available files explicitly.

The Map Forge sidecar owns slots and placement. Props & Terrain supplies each component's source identity/revision, real file and measurements. Reuse `composition.anchor` and `shadow` from `props_spec` as requested values; record observed alignment separately. At the handoff, include:

- Source path, revision and hash with the hashing convention named. Distinguish the map compiler's canonical JSON hash from a file-byte hash.
- Asset/object/version IDs, generating props source and revision/hash, actual image path, dimensions and file-byte SHA-256. Never substitute requested dimensions for measured ones.
- Ground footprint and anchor, asset anchor in full-canvas normalized coordinates, explicit board frame/units, scale, clockwise rotation, layer order and baked/separate shadow policy. Include actual alpha bounds and padding without calling them a ground footprint.
- Where registration is required, declare an anchor tolerance appropriate to the intended scale before review. Record the target and observed ground anchor in board pixels and their measured deviation; an uncertain image anchor leaves registration unresolved.
- Intended change region including shadow reach, affected neighbors/access routes, conserved regions and the base composition revision/hash. For an initial assembly, the base can be absent; replacements require the actual base.
- Separate candidate, review, production-selection and user-approval states, plus output files and assembly evidence when it actually runs.

In the template, all unqualified placement and region coordinates are board pixels with upper-left origin and positive y down. Rectangles are `[x,y,width,height]`; alpha bounds are `[left,top,right,bottom]` with exclusive right/bottom. `ground_to_board_affine` is `[a,b,c,d,tx,ty]`, so `x'=a*x+c*y+tx`, `y'=b*x+d*y+ty`. For raster assembly, a source pixel point `p` is placed at `board_anchor_px + R_clockwise(rotation_deg) * (scale_board_px_per_asset_px * (p - asset_anchor_px))`. Convert normalized anchor to actual raster dimensions first. Do not infer scale from alpha bounds or stretch a roof to fill its plot. Record an explicit transform extension if another editor needs different semantics.

Only perform assembly when the user has authorized it, using the available editing/compositing workflow and its permissions. Use exact transforms and layers in an editor/code workflow when exact placement matters. If those capabilities are unavailable, deliver the placement handoff and name the gap. Do not claim a generation prompt executed deterministic assembly. Keep accepted components versioned and replace only affected pieces. Whole-map generative harmonization after acceptance is a separate requested operation because it can repaint conserved regions.

## Review the result, not the plan

Keep these gates and evidence separate. Mark a gate passed only for the inspected artifact/revision and stated scope.

| Gate | Evidence |
| --- | --- |
| Shape and identity | Actual candidate crop/full image shows the expected connected mass, open courts, silhouette and signature. A nearby tree or plausible roof does not prove the intended identity. |
| Placement and access | Correct district/relative order establishes overview placement only. For required registration, compare the target `board_anchor_px` with the observed ground anchor, record Euclidean deviation in board pixels, and check it against the declared tolerance. Check entrances, lanes, courts and neighbors on the actual result. Uncertain alignment stays unresolved; identity alone cannot pass metric registration. |
| Composition | At seams, compare camera, material scale, edge treatment, occlusion, light and shadows against adjacent accepted pieces. |
| Display size | View the intended overview and detail sizes; confirm the identity cues survive at those sizes. Enlargement of a crop does not add evidence of missing detail. |
| Player disclosure | Inspect the final player image and its shared references/overlays for secrets and unintended text. |
| Source integrity | Verify IDs, source revision/hash, unchanged ground geometry, actual file dimensions/hashes, unique slot-to-group assignments and recorded transforms. This gate does not certify the painting. |
| Native setup | After authorized import, check grid, player display, interaction and save/reopen in Atlas. A composite remains unimported until observed. |

For dense identity work, use independent review when available and authorized. Give reviewers the source expectations and actual candidate image, and require observed group enclosures/crops and visual reasons. Do not feed them another reviewer's passing assignments as proof. Reconcile overlapping or conflicting assignments against the actual pixels and district relationships before accepting a combined ledger; agreement on a key name can still refer to different groups. Keep an uncertain match unresolved and do not assign the same visible group to two source identities.

On a narrow replacement, recheck the changed piece, affected neighbors, access, seams and shadow extent, then compare conserved regions with the prior accepted composition. A global generation edit widens the regression scope because its changes may be unbounded. Scale review to the actual impact; a tiny isolated prop edit does not automatically require a full-city identity audit.

On resume, read the saved sources, pins, component versions and review evidence. Reconcile stale hashes before continuing. `proposed` means a plan; `reviewed` means inspected with findings; `accepted` means selected for production by the recorded authority and criteria; `user_approved` requires actual user approval. Acceptance of source, a component, a composition and native play each has its own scope.
