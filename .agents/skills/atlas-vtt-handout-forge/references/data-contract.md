# Editable handout source

Use version 1 JSON, validated by `scripts/handout_spec.py`. A single document and a set use the same contract; no native Atlas envelope is implied.

| Field | Meaning |
| --- | --- |
| `schema_version`, `set_id`, `revision` | Version 1, stable set ID, positive revision. |
| `locks` | Existing JSON pointers, such as `/documents/0/wording/content`. Revisions preserve these definitions. `/revision` is automatically managed and cannot be locked. |
| `art_direction` | Shared, public visual direction. |
| `documents` | Nonempty ordered list of individually identified documents. |
| `references` | Reference records with unique `ref_id`, `locator`, `roles`, `status`, `gm_only`, `use`, and `ignore`. |
| `gm_notes` | Optional private context, never exported by the helper. |

Each document requires `asset_id`, `kind`, `gm_only`, `wording`, `material`, `illustration`, `typography`, `layout`, and `reference_ids`. Supported kinds are `letter`, `poster`, `journal`, `contract`, `inscription`, and `other`. `wording` contains `content`, `approval` (`draft` or `approved`), and `basis`. Here `approved` means authorized as final for the task: supplied exact wording, user-approved wording, or an explicit user delegation to choose final wording. Record that existing authority in `basis`; no additional approval round is implied. Basis is an operator record retained only in the master, not the public brief or composition. Empty wording is valid draft input. Composition requires nonempty final wording and a nonempty basis. Keep drafts when requested or consequential wording remains unresolved. `edit_target_id`, when present, must reference an `edit_target` role and be included in `reference_ids`.

Use reference roles such as `style`, `material`, `illustration`, `seal`, `glyphs`, or `edit_target`. Status is `uninspected`, `inspected`, or `unavailable`. Keep unavailable observations empty. An inspection record is a claim made by the author; validation cannot establish that pixels were viewed. The player brief omits unresolved locators and directives. A public document needing a private reference is incomplete for player rendering until the reference is safely resolved or replaced.

`typography` defines `family` (`serif`, `sans-serif`, or `monospace`), `font_px`, `line_height`, and six-digit hex `ink`. The HTML helper uses system generic fonts, not guaranteed historical lettering or a bundled font. For custom glyphs or a specific face, use an appropriate deterministic compositor and record the actual font. Source wording allows Unicode and ordinary whitespace; NUL, unsupported control characters, and lone Unicode surrogates are rejected because HTML cannot preserve them faithfully.

`layout` defines integer `width_px`, `height_px`, `margin_px`, and `reserved_illustration_px`. The latter reserves the bottom of the page for illustration. Dimensions must be positive with room for at least one line after margins and reservation. These are requested page dimensions, not observed raster measurements. HTML wraps text visually and expands rather than silently hiding overflow; final page size and fitting require visual review. The helper is a useful one-column starter, not a desktop publishing engine. For columns, complex contracts, curved inscriptions, redactions, or marginal illustrations, retain the same exact wording and use a suitable deterministic layout tool.

Revisions use `{ "expected_revision": 1, "changes": [{ "path": "/documents/0/layout/margin_px", "value": 90 }] }`. Only existing leaf values can be replaced. Collections, identities, approval flags/basis, revision, schema version, reference inspection status, `gm_only`, reference bindings, and lock definitions require a deliberate master edit. Wording replacement resets to draft unless the caller provides `--wording-basis` recording existing user authority for the final replacement. Changing a reference locator resets inspection and clears old observations. Pointer comparison handles ancestors and descendants so replacing a parent cannot bypass a child lock; implicit resets are checked against locks too. Outputs are created exclusively; provide a new path to retry and retain older approved files.

Three guarded failure cases justify the helper: exact text altered by escaping or HTML normalization, private content exported with public documents, and a broad/stale revision drifting locked or unrelated source data. It has no image API, vault access, network client, or publishing authority.
