# Editable props contract

`/revision` is automatically managed and cannot be locked. Validation rejects that lock before any revision can change it.

Use one private `props_spec` master. `schema_version` is `1.0`; `spec_id` and every ID are stable. A set contains `assets`, shared `art_direction`, role-tagged `references`, optional `gm_notes`, recorded `assumptions`, and source `locks` expressed as JSON Pointers. `revision` is a positive integer. The starter is structurally valid but intentionally incomplete; its blank subject/style and unknown footprint block render readiness.

Each asset records:

| Field | Meaning |
| --- | --- |
| `object_id`, `asset_id` | Reusable object identity and distinct image identity; related variants share only object identity |
| `kind`, `description`, `materials` | Map object family and visible appearance, without private lore |
| `viewpoint`, `orientation` | Camera treatment and object direction relative to image top |
| `footprint` | Width and length in a named world unit; never inferred from the raster |
| `composition` | Whole object, four-edge clear margin fraction, object-only/base decision, normalized anchor `[x,y]` in the full canvas with origin at top left |
| `shadow` | `none`, `contact`, or `cast`, cast direction clockwise from image top, reach as a fraction of object's long dimension |
| `output` | Requested pixel width/height or null, background `transparent` or `solid`, public backdrop description, intended preview long edge in pixels |
| `reference_ids` | Only references actually required by this piece |
| `edit` | Optional approved inspected target reference ID, requested change, and visual invariants |
| `gm_only` | Private piece excluded from player compilation |

`art_direction` records medium/rendering style, palette, edge treatment, and lighting. Maintain coherent set conventions in these shared fields. An asset's explicit object colors take precedence over the shared palette, allowing a narrow color revision without recoloring the set. Do not treat examples as campaign canon.

References have `reference_id`, `locator`, `role` (`identity`, `style`, `viewpoint`, `material`, `scale`, `edit_target`), `inspection` (`inspected`, `uninspected`, `unavailable`), `use`, `ignore`, `approved`, and `gm_only`. Inspection is a saved assertion; the helper does not view files, authenticate URLs, or confirm user approval. Access the actual image in the current run before sending it to the renderer. Unused references never enter compilation. Player assets cannot depend on GM-only references.

Use `gm_notes` only for private context and GM-only assets for private visible variants. Compilation uses an allowlist of fields and exports no GM notes. It cannot identify secrets pasted into public prose, so review the filtered brief before sharing or rendering. A GM compilation can include private visible assets and must remain private.

Revision files use `expected_revision` and nonempty `changes`, each with `path` and `value`. Only existing fields can be replaced. Stable IDs, schema version, revision, and lock definitions are protected. Asset/reference collection replacement is refused. A parent or descendant of a locked field is protected as well. `--allow-locked` names exact authorized locks, not arbitrary bypass prefixes. Unknown paths, stale revisions, duplicate paths, overlapping changes, no-op changes, and invalid updated specs fail without output. The helper does not add or remove assets; deliberately edit and validate the master when the user requests those operations.

Commands create output files exclusively. Pick a fresh output path; a repeated invocation cannot overwrite source or a prior approved artifact. The source hash identifies the exact source bytes for a compiled brief, not the pixels that an image tool generated. No helper generates images or changes Atlas.
