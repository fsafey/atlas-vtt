# Token source contract

Use one `token_spec` for one asset or a coherent set. This format is independent of native Atlas metadata. `schema_version` is 1, revision starts at 1, and IDs are stable lowercase identifiers with digits, underscores, or hyphens. The JSON schema defines structural fields; the helper also checks cross-record identity, disclosure, and revision invariants.

| Source field | Meaning |
| --- | --- |
| `spec_id`, `revision` | Authoring identity and monotonically increasing source revision. |
| `subjects` | One shared visible identity per subject, with `subject_id`, public name, `identity_reference_ids`, nullable `portrait_origin`, `gm_only`, and private `gm_notes`. |
| `visible_identity` | The Portrait Forge identity shape: form, nullable apparent age, counted anatomy entries (`feature`, `count`, `details`), face/head, coloring, distinctive features, clothing, and equipment. All descriptions are intentionally player-safe. |
| `portrait_origin` | Imported portrait asset ID, source revision/hash, approved-image reference ID, and original approval assertion. It records provenance, not executed inspection. The origin cannot be changed through the narrow revision helper. |
| `assets` | Stable `asset_id` and subject binding, public title/use, generate/edit intent, token kind, viewpoint, pose, background, border, composition, output requests, art direction, references, nullable edit target, constraints, and `gm_only`. |
| `kind` | `portrait_circle`, `top_down`, or `creature_cutout`. A top-down token uses `viewpoint: orthographic_top_down`; a side or tilted figure uses cutout presentation. |
| `background` | Mode `unspecified`, `solid`, or `transparent`, with a description. Top-down and cutout defaults are transparent; explicit opaque bases or shadows remain allowed. |
| `border` | `atlas_ring`, `baked`, or `none`, with a concrete description. Atlas framing and circular portrait sources require square requested dimensions/ratio. A baked border recommends native ring off. Explicit requested borders remain allowed on other token kinds. |
| `composition` | Nullable `safe_margin_percent` from canvas edges plus important identity/crop features. This is a request, not a geometric crop guarantee or measurement. |
| `output` | Nullable width/height and `[width,height]` aspect ratio, plus chosen `tabletop_sizes_px` for review. Supply both dimensions or neither; dimensions must agree with the ratio. These are targets, not provider controls or actual measurements. |
| `art_direction` | Portrait-compatible medium, rendering, palette, lighting, and mood. |
| `references` | ID, actual locator, role, inspection state, use/ignore traits, identity approval, and privacy. Roles are identity, style, pose, clothing, edit target, and quality. Uninspected/unavailable references must have empty traits and no identity approval. |
| `locks` | Existing nonroot JSON Pointer paths, excluding `/revision`. Keep arrays in stable order so pointers continue to identify their records. |
| `assumptions`, `gm_notes` | Public choices and private master-only context. Appearance needed for the image must also appear in visible identity/presentation. |

Keep empty strings, arrays, and null requirements for unknowns rather than inventing observations. A structurally valid source may remain incomplete. The starter is deliberately incomplete. Identity anchors require the identity role, and an edit requires an edit-target reference. Public consumers cannot depend on a GM-only reference; mark the dependent variant or subject private instead of quietly discarding its identity requirement.

## Public compilation

`compile` defaults to player audience. It excludes private subjects/assets, all GM notes, unused references, and uninspected reference locators/directives. A GM compilation may contain private visual variants and must be treated as private, but still excludes notes. The helper cannot identify secret facts embedded in public names or prose; review the filtered output before sharing it.

Each brief carries subject/asset IDs, visible identity, presentation, art direction, used inspected references, unresolved reference IDs, concrete readiness issues, prompt text, and an Atlas display hint. The hint is not a native token or performed import. Output metadata includes source ID, revision, and SHA-256 of canonical JSON (`sort_keys=True`, compact separators, UTF-8 with `ensure_ascii=False`); it is not a hash of original file bytes.

Readiness needs visible appearance, intended use, viewpoint, a background choice, and no unresolved used references. An imported approved portrait also requires the receiving workflow to confirm its identity approval. These are source assertions. The helper does not view images, verify permission, render assets, or prove small-size readability. Text output requires exactly one selected visible ready token, preventing accidental concatenation of sets.

## Portrait handoff consumption

`from-handoff` accepts the exact output of `atlas-vtt-portrait-forge/scripts/portrait_spec.py handoff`: subject ID, portrait asset ID, source revision/hash, nonempty available local `approved_image`, identity, art direction, public approved identity/style references, approval basis, `token_status: not_created`, and `atlas_status: not_imported`. It rejects extra fields and unrelated references rather than importing an entire private portrait master.

The new source retains the subject ID and identity exactly, assigns a new token asset ID, stores portrait provenance, and locks the imported identity. The approved portrait becomes a required identity anchor. Every imported reference starts uninspected with no traits or identity approval, including references whose portrait-side record claimed inspection. The handoff's art direction and identity requirements remain intact; use/ignore observations must be reconstructed after actually viewing each reference. Keep the original handoff beside the token source to compare those prior assertions if needed.

After viewing, record inspection and concrete traits. Confirm asserted prior approval from the actual user/session context before setting `approved_identity` on the portrait anchor. The importer validates file existence only; it does not decode that file or approve it. A missing file blocks identity-dependent rendering, and the imported source remains incomplete until those checks occur.

## Narrow revisions

A change file contains only `expected_revision` and a nonempty array of `{path, value}` replacements. Paths must already exist; overlapping replacements fail. The helper copies the source, checks the revision, applies changes, checks locks and stable IDs/subject bindings/provenance, validates, then increments revision. A no-op fails without incrementing revision. Output creation is exclusive and inputs cannot be overwritten.

Existing subject, asset, and reference records retain their IDs and positions. Appending records via whole-array replacements is allowed if existing records remain in order. Removing/reordering records, rebinding assets, changing source identity/lock definitions, or rewriting portrait provenance needs a deliberate master edit with reviewed pointer targets, incremented revision, and validation. This does not itself imply an extra permission request unless unresolved authority or a locked field requires it.

An explicit user instruction can authorize a locked value change. Pass only its exact existing pointer with `--allow-locked`; the document cannot authorize itself. Ancestor replacements must still preserve every other locked descendant. Locks protect JSON, not rendered pixels.

## Measurement and local checks

`inspect-image` reads actual pixels without editing them. It reports file, format, dimensions, alpha-channel presence, alpha extrema, nonopaque/fully transparent fractions, and nontransparent bounds. An opaque RGBA file has alpha but no transparency; a palette PNG can have transparency without an explicit alpha band. Entirely transparent images have null bounds. Bounds include stray pixels and shadows and do not semantically identify the subject. Visual, tabletop, and approval states remain unverified.

Run from this skill directory:

```sh
uv run --with 'jsonschema>=4.23,<5' --with 'pillow>=11,<13' python -m unittest discover -s tests -v
uv run --with 'ruff>=0.15,<1' ruff check scripts tests
uv run --with 'pyright>=1.1,<2' --with 'jsonschema>=4.23,<5' --with 'pillow>=11,<13' pyright scripts tests
uv run --with 'pyyaml>=6,<7' python /Users/farieds/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

Synthetic-image tests establish metadata behavior only. The tests consume the actual Portrait Forge export and exercise source filtering, reference failures, stable IDs, stale revisions, lock protections, token framing, explicit treatment overrides, CLI readiness, and output preservation. No generation, real subject review, import, or successful tabletop use is inferred from them.
