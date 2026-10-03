# Heraldry source contract

Use one source for a standalone symbol or coherent set. `schema_version` is 1 and `revision` starts at 1. IDs use lowercase letters, digits, hyphens, or underscores. Keep existing collection order stable because locks use JSON Pointer paths.

| Field | Purpose |
| --- | --- |
| `spec_id`, `revision`, `locks` | Stable source identity, revision counter, and exact existing field paths. |
| `factions` | One definition per visual identity: `faction_id`, public `name`, `identity`, `reference_ids`, optional `emblem_reference_id`, optional `consistency_anchor_asset_id`, `gm_only`, and private `gm_notes`. |
| `identity` | Shared `motif`, `silhouette`, `arrangement`, `palette` role descriptions, `distinctive_marks`, and `constraints`. There are no carrier-specific identity overrides. |
| `assets` | Distinct `asset_id`, `faction_id`, title/use, `kind`, intent, carrier, background/output, lettering, style, references, edit target, constraints, and visibility. |
| `kind` | `coat_of_arms`, `emblem`, `insignia`, `sigil`, `seal`, `banner`, or `flag`. |
| `carrier` | Material, shape, viewpoint, orientation, composition, and positive `reading_size_px` for review. Carrier changes cannot change the base motif by implication. |
| `background` | Mode `unspecified`, `solid`, or `transparent`, plus description. |
| `output` | Nullable width/height, supplied together, and nullable `[width,height]` aspect ratio. Dimensions must agree with ratio. Requested values are targets. |
| `lettering` | Exact `wording`, `mode` (`none`, `raster_verify`, or `compose_later`), and placement. No-text mode requires empty wording. Other modes require nonempty wording/placement. |
| `references` | Stable ID, locator, role (`emblem`, `style`, `material`, `edit_target`), inspection (`uninspected`, `inspected`, `unavailable`), approval (`not_requested`, `pending`, `user_approved`, `rejected`), `use`/`ignore` traits, visibility, and private notes. |

Uninspected/unavailable references cannot assert visual traits or user approval. A faction's `emblem_reference_id` must resolve to an inspected emblem reference; it need not carry new user approval when a render was already authorized. Existing approved references should be selected, not silently substituted. JSON records assert inspection and approval; validate them against session evidence and the actual image before use.

For a fresh set, select one requested public asset with a clear emblem view as the faction's consistency anchor. It must belong to that faction. Prefer a plain emblem when requested; any supported carrier can anchor a set if its emblem can be inspected clearly. A seal-and-flag request does not require an extra emblem asset. Dependent carrier briefs remain incomplete until the resulting image is inspected, recorded, and selected as `emblem_reference_id`. That reference role describes the identity to reuse, even when the image shows wax or cloth. The anchor's own brief can be ready before that. Keep the anchor ID afterward as provenance; an inspected emblem reference satisfies the dependency. An explicitly supplied canonical emblem can be used without an anchor asset.

Edit intent requires an `edit_target_ref` with edit-target role; generation intent cannot have one. Public consumers cannot depend on private references. A faction's visibility governs all its assets even if an individual asset was not separately marked private. All GM notes are excluded from both player and GM briefs; GM briefs may include private visible designs and their used references.

## Compilation

Compilation validates first, then selects assets visible to the chosen audience and emits their shared identity, carrier presentation, style, lettering plan, and used inspected references. Unused records are omitted. Unresolved references omit locators and directives. Player selection of a private asset fails without exporting a partial source.

`--text` requires exactly one render-ready brief. Unresolved briefs remain available as structured JSON for further authoring, but plain-text export fails before creating an output file so missing dependencies cannot be lost.

`render_ready` means the required authoring fields and declared reference/anchor records are present, not that a render was executed. Exact lettering scheduled for deterministic composition remains separate from the image instructions: the image prompt requests a blank reserved area, while the unchanged string stays in the brief's `lettering` object. Complete the final composition before delivering a finished asset.

Compilation includes source revision/hash and separate initial `image: not_generated` and `atlas: not_imported` statuses. Those statuses describe compilation, not a replacement for a saved render-review record. Share only a reviewed audience compilation, not the private source.

## Controlled changes

A change file contains only `expected_revision` and a nonempty `changes` array of `{path,value}` replacements. Paths must address existing fields. The helper refuses stale revisions, duplicate/overlapping change paths, invalid pointers, managed-field changes, collection reordering/removal, identity rebinding, and output overwrite.

Locks also protect descendants and ancestors of the locked path. `--allow-locked` names exact existing locks whose changes the user authorized. The helper does not establish that authorization itself. Unknown authorization paths fail. A revision increments only after validation and leaves the input untouched. Array membership additions/removals need a deliberate master edit saved as a new source version with incremented revision, followed by validation; the narrow revision helper does not provide a general patch language.
