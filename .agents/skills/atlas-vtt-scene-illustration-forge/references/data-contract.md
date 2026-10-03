# Scene source and revision contract

Use one source for a single reveal or coherent set. `schema_version` is 1; `revision` begins at 1. `spec_id`, `location_id`, `asset_id`, and `reference_id` are stable lowercase IDs. This is authoring data, independent of native Atlas scene data.

| Source field | Purpose |
| --- | --- |
| `locations` | Define public `name`, `description`, recurring `architecture`, `landmarks`, and `identity_reference_ids` once. `gm_only` makes the location and its consuming assets private; `gm_notes` holds nonvisual private context. |
| `assets` | Each image has a distinct `asset_id`, stable `location_id`, public `title`, `kind` (`location_reveal` or `dramatic_scene`), `intended_use`, and `gm_only`. |
| `moment`, `visible_changes` | Visible action and per-image state changes. A snow, damage, or seasonal variant changes this image only. Describe a changed state precisely; preserve identity elements the request did not change. |
| `composition` | Free-text `viewpoint`, `framing`, `focal_point`, `depth`, and `visible_figures`. These describe the camera and visible participants; they do not prescribe fixed perspectives or game coordinates. |
| `atmosphere` | Per-image `time`, `weather`, `lighting`, and `mood`. Keep light sources and shadow direction understandable. |
| `art_direction` | Per-image `medium`, `rendering`, and `palette`. Copy the approved direction across coherent assets when requested, then change only the selected variant's fields. |
| `background` | `mode`: `unspecified`, `opaque`, or `transparent`; `description` explains the treatment. A transparent vignette is valid. Avoid describing an opaque backdrop when transparency is requested. |
| `output` | Nullable `width_px`, `height_px`, and `aspect_ratio` as `[width,height]`. Specify dimensions together; supplied dimensions must match the ratio. Values are requests, never measurements or provider controls. |
| `intent`, `edit_target_ref`, `edit_scope` | `generate` has null edit inputs. `edit` requires a reference with role `edit_target`, plus `edit_scope.change` and `edit_scope.preserve`. The actual base image must be inspected and available to the renderer. |
| `references` | `reference_id`, actual `locator`, `role` (`location_identity`, `style`, `composition`, `character_identity`, `edit_target`, `quality`), `inspection` (`uninspected`, `inspected`, `unavailable`), `use`, `ignore`, and `gm_only`. Trait claims require inspection. |
| `lettering`, `constraints` | Exact requested visible text and other public visual requirements. Empty lettering means no requested words; review unwanted lettering separately. |
| `locks` | Existing nonroot JSON Pointer paths. Keep array order stable so pointers continue to target the same records. `/revision` is managed and cannot be locked. |
| `assumptions`, `gm_notes` | Recorded public authoring assumptions and private context. Assumptions do not silently fill missing source fields or authorize new work. |

Use empty strings/lists and null dimensions for unspecified values. The starter is structurally valid but incomplete. Missing style details do not block rendering when the user has allowed the agent to choose. References in examples are empty because no images were actually inspected.

The helper checks structure, unique IDs, location and reference bindings, disclosure dependencies, inspection assertions, edit inputs, paired dimensions, ratio arithmetic, and existing lock paths. It does not prove perspective, consistent architecture, prose disclosure, image availability, or successful rendering. An inspected reference record remains an assertion until verified in the active task.

## Filtered compilation

`compile` defaults to `--audience player`. It omits private assets and all assets on private locations. Public consumers cannot require private references: mark the consumer private or correct the requirement instead of silently losing a reference. Location identity references are automatically included for each reveal. Only used inspected references appear, and all `gm_notes`, unused reference records, and private master fields are absent from either audience's compilation.

Uninspected and unavailable references emit only unresolved IDs, excluding their locators and trait directives. They make `render_ready` false. A location description, viewpoint, focal point, and intended use are needed for readiness; dramatic scenes also need a visible `moment`. Selecting a hidden or unknown asset fails. `--text` requires exactly one ready brief so a set cannot accidentally become a single combined render.

The output has `spec_id`, `source_revision`, `source_sha256`, `audience`, and `briefs`. Each brief includes the public location identity, presentation fields, inspected references, unresolved IDs, readiness findings, and an image prompt. SHA-256 uses canonical sorted JSON with compact separators and UTF-8; it identifies source content, not original file bytes. Compilation does not render, download, approve, import, or inspect images.

Review shared prose before player delivery. Secret meaning cannot be detected mechanically. Never write secret facts into public names, negative constraints, or reference-use text. A GM compilation may contain private visual variants and is a private image brief even though GM notes remain excluded.

## Guarded revision

A change file contains only `expected_revision` and a nonempty `changes` array of `{path,value}` replacements. Each path must already exist. The helper applies changes to a copy, rejects overlapping paths, preserves existing IDs/order and asset-location bindings, compares locks, validates, and increments the revision. Collections may be replaced to append entries, but existing entries retain their positions and identity. Unspecified values remain unchanged.

`schema_version`, `spec_id`, `revision`, and lock definitions are managed fields. Removing/reordering entries or rebinding an asset requires a deliberate master edit with lock review, revision increment, and validation. It does not imply additional permission unless an unresolved locked change requires it.

For an explicitly authorized lock change, pass only its exact existing path through `--allow-locked`; change documents cannot grant authorization. Replacing an ancestor still preserves every unapproved descendant lock. The CLI refuses to overwrite either input or an existing output, so repeat runs preserve earlier artifacts.

## Artifact and review record

Save review evidence alongside the deliverables, outside the editable source:

```json
{
  "asset_id": "reveal-01",
  "location_id": "location-01",
  "source_revision": 1,
  "file": null,
  "brief": "ready",
  "image": "not_generated",
  "atlas": "not_imported",
  "measurements": null,
  "visual_review": "not_run",
  "findings": []
}
```

Populate file and measurements only from an actual artifact. Record user approval separately when relevant. Resume from source and artifact records instead of repeating completed image calls.

## Local validation

```sh
uv run --with 'jsonschema>=4.23,<5' python -m unittest discover -s tests -v
uv run --with 'ruff>=0.15,<1' ruff check scripts tests
uv run --with 'mypy>=1.19,<2' mypy --ignore-missing-imports scripts/scene_spec.py
uv run --with 'pyyaml>=6,<7' python /Users/farieds/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

These checks exercise source and CLI behavior. They do not generate campaign artwork or establish in-app Atlas acceptance.
