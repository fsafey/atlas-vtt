# Data contract, geometry and revisions

## Three documents, three jobs

`map_spec` is the complete editable source. `compiled.image_instructions` is the image-facing description derived from it. `compiled.postproduction` is a grid, labeling, marker and export plan. `compiled.atlas_setup` adapts that plan to Atlas VTT field conventions and its manual import journey. Do not conflate them.

The optional Python compiler returns a full response envelope containing both source and derived data. That envelope is a **private master** because the source can contain GM information. `--render-brief --audience player` returns just the filtered compiled object; `--text --audience player` returns only the image instructions. Public free-text fields still need human disclosure review.

`templates/starter-brief.json` is deliberately small and is not a schema-valid full map. The authoring agent expands it into the canonical format through questions and explicit assumptions. The command-line validator expects the canonical format, not a starter brief or a whole response envelope.

## Canonical field map

| Field | Meaning | Where it goes |
|---|---|---|
| `version`, `id`, `revision` | Schema version, stable map identity, revision counter | Versioning, hash, change control |
| `title`, `map_type`, `purpose` | What the map is and what it is for | Deliverable instructions; title is not automatically printed |
| `inspiration` | Premise, mood, novelty, motifs, scoped references | Composition and art direction |
| `canvas` | Aspect ratio, delivery pixel target, edge safety inset | Composition; export plan |
| `style` | Explicit medium, linework, palette, lighting, hierarchy, border | Visual instructions; `preset` is an authoring label only |
| `environment` | Terrain structure, season, time, weather, allowed exceptions | Visible setting |
| `entities` | Stable dictionaries of places, regions, objects and hazards | Object-by-object rendering requirements |
| `connections` | Route geometry and traversable topology | Physical route instructions; reachability checks |
| `relationships` | Required geographic/physical relations | Explicit spatial constraints |
| `gameplay` | Grid/scale, entries, goals, movement widths and affordances | Spacing rules; VTT setup; reachability checks |
| `annotations` | Lettering, clear zones and marker destination | Painted only when requested; otherwise separate plan |
| `production` | Audience, variant, action, base image, edits, exclusions, format | Render handoff and export intent |
| `locks` | JSON Pointer paths that require explicit approval to alter | Source editing protection, not pixel constraints |

All canonical fields are present, even when a valid empty array or null is appropriate. Unknown keys fail schema validation instead of being silently discarded. Extend the schema intentionally when adding a new kind of control.

## Geometry

All placement geometry uses the full image rectangle. The origin is **upper-left**. North is up. Positive x moves right; positive y moves down. Values are normalized fractions from 0 to 1.

`bounds: [x, y, width, height]` describes a target bounding box. For example, `[0.43, 0.16, 0.22, 0.20]` means left 43%, top 16%, width 22%, height 20%. It does not mean x-max 22%. Width and height must be positive; the entire box must fit within the canvas.

An optional entity `placement.path` is an ordered polyline of `[x, y]` points in the same full-canvas coordinate space. Use it for a river or elongated region. Every point must be inside the entity's box. A path is not a closed polygon, collision outline, or pixel-perfect mask.

Connections use their own ordered `path` plus a logical chain `from -> via[] -> to`. Both describe the same intended route: one spatially, one topologically. They are not unrelated route alternatives. The graph assumes each `traversable: true` connection is usable in **both directions**. One-way paths are not implemented in version 1.0.

For fine control over individual objects, use separate entities, not a giant prose paragraph or one grouped quantity. Relative relationships supplement coordinates; they do not override conflicting coordinates without review.

Basic cardinal validation compares box centers. `inside` checks box containment. More demanding relations such as `crosses`, `flows_into`, `adjacent_to` and `avoids` are compiled into requirements but **not geometrically proven** by the script.

## Count, visibility and lore

`quantity` counts the item represented by that entity. One forest means one forest area, not one tree. Three monoliths means three countable monoliths within the specified region. Extra individually controlled objects deserve separate IDs.

`visibility: public` means the feature can appear in player art. `gm_only` removes it from player rendering and player overlays. A secret room that should not be visible needs `gm_only`; a publicly visible ruin with a hidden backstory stays public and puts that backstory in `gm_notes`.

`gm_notes` never enters the image instructions. In GM compilation it appears in a separate private notes object. The compiler cannot reliably detect a secret embedded in a public description, premise, relationship detail, must-show item or connection description. Keep every shared field player-safe and review it before rendering.

A public route cannot terminate in a hidden entity, and a public label cannot identify one. The validator catches those explicit references. Do not expose secret positions through exclusion instructions in a player prompt.

## Square-grid sizing

With a zero offset, a 32 by 24 cell map at 100 pixels per cell has a **delivery target** of 3200 by 2400 pixels. The image generator still has to produce suitable art, and the result must be inspected and aligned.

A nonzero `offset_px` records a shifted grid origin. The validator then skips the simple full-canvas multiplication check and emits a calibration warning because partially visible edge cells require separate treatment.

`units_per_cell` is game distance, such as 5 ft, not pixel resolution. `pixels_per_cell` is image sampling for square cells, not physical DPI. Do not interchange these quantities.

A top-down map can still fail tactical acceptance despite perfect pixel arithmetic: walls may drift between cells, doors may be too narrow, or furniture may seal a route. These require visual and VTT checks.

## Hex-grid sizing

`hex_orientation` is `pointy_top` or `flat_top`. `hex_cell_width_px` is the horizontal bounding width of a hex, not a universal “pixels per cell” value. `pixels_per_cell` is null for hexes. Rows and columns may remain null until the destination VTT is calibrated.

The compiler does not derive a rectangular raster size from hex row/column counts. Pitch, stagger, orientation and partial edge cells matter. The actual overlay must be aligned to the actual raster. For Atlas, pointy-top horizontal width equals native grid.size; flat-top horizontal width must be multiplied by sqrt(3)/2. The compiled atlas_setup contains this conversion. These remain calibration candidates until checked against the actual raster.

## Labels and markers

A label has exact text, a normalized anchor, rotation, optional entity association and disclosure level. `label_mode: postprocess` means no lettering goes into the art prompt. `baked` includes exact quoted text as a renderer request. `none` preserves any source labels for future editing but emits no labels.

Anchors are preliminary layout targets. Verify them against the generated artwork before compositing. `clear_zones` asks the painter to leave quieter texture for overlays; it does not request blank rectangular holes.

`markers: vtt` produces candidate marker positions, not actual interactive pins. The Atlas setup compiler provides field hints and GM note-pin candidates; no scene, wall or lighting export is implemented.

## Revisions, variants and locks

The source carries its own revision. A saved patch begins with a `test` of `/revision`. Supported operations are `test`, `add`, `remove`, and `replace`, using standard JSON Pointer escaping (`~1` for `/`, `~0` for `~`). This is a **subset**, not a full JSON Patch implementation.

The patch helper is atomic: it changes a copy, enforces locks, validates the result, then increments the revision. It never overwrites the input file. It refuses direct patch changes to `/version`, `/id`, `/revision`, or `/locks`; edit identity and lock definitions deliberately in the master file.

`--allow-locked /entities/citadel/placement` explicitly authorizes that exact locked pointer for one patch. It does not remove the lock. The skill should use it only after the user approves that named change.

The compiler hash uses sorted keys, UTF-8, compact separators, and SHA-256 over the canonical JSON. It identifies the input spec, not an image seed or a promise of reproducible rendering. Natural-language changes must be reflected in the source, then recompiled.

A moonlit spec and a daylight spec can have identical geometry and still generate different pictures. For an actual visual variant, supply the approved base image to a later image-editing step and constrain the edit. `base_image_reference` is a locator that must be resolved by that workflow; this script does not open or attach it.

## Validation scope

**Automatically checked:** schema, unique dictionary keys on file loading, IDs, bounds/path containment, selected relationships, declared two-way route reachability, minimum declared route widths, basic disclosure links, view/profile compatibility, and applicable square-grid arithmetic.

**Not automatically checked:** natural-language contradictions, hydrology, elevation, river/bridge intersections, true corridor width in a rendered image, wall openings, visual overlap, image quality, reference availability, native renderer capabilities, image file metadata, marketplace compliance, or VTT import.

The bundled schemas use `.invalid` URI namespaces to identify themselves; these are not hosted downloads. The test suite registers the bundled schema files locally and makes no schema-network requests.
