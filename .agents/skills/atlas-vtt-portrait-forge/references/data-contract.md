# Portrait source contract

Use one source for a single portrait or coherent set. `schema_version` is 1; `revision` starts at 1. `spec_id`, `subject_id`, `asset_id`, and `reference_id` are stable lowercase IDs with digits, hyphens, or underscores. `subjects`, `assets`, and `references` are arrays; locks use JSON Pointer paths into this source. Keep existing order stable so locks continue to identify the same records.

## Source fields

| Field | Meaning |
| --- | --- |
| `subjects` | Define each subject once: public `name`, `visible_identity`, `identity_reference_ids`, `gm_only`, and private `gm_notes`. |
| `visible_identity` | `form`, nullable `apparent_age`, counted `anatomy` entries (`feature`, `count`, `details`), `face_head`, `coloring`, `distinctive_features`, `clothing`, and `equipment`. All are player-safe visual descriptions. |
| `assets` | Each portrait's `asset_id`, `subject_id`, public `title`, `intended_use`, `intent` (`generate` or `edit`), `framing` (`face`, `bust`, `full_body`), `viewpoint`, `pose`, `expression`, `background`, `output`, `art_direction`, `reference_ids`, nullable `edit_target_ref`, `constraints`, and `gm_only`. |
| `wardrobe` | Optional per-asset object with `clothing` and/or `equipment` arrays. Supplied arrays replace the subject's defaults only for this portrait; omitted fields inherit defaults. An empty array deliberately removes clothing or equipment. Keep the asset's palette consistent with its requested outfit. All override prose must be audience-safe. |
| `background` | `mode`: `unspecified`, `solid`, `environment`, or `transparent`; `description` gives the concrete treatment. Do not describe an opaque scene for transparent mode. |
| `output` | Nullable `width_px`, `height_px`, and `aspect_ratio`. Both dimensions must be supplied together. A ratio is `[width,height]`; explicit dimensions must match it. These are requests, not provider arguments or measured output. |
| `art_direction` | `medium`, `rendering`, `palette`, `lighting`, `mood`. Describe materials in the appropriate identity, rendering, or constraint field. |
| `references` | `reference_id`, actual `locator`, `role` (`identity`, `style`, `pose`, `clothing`, `edit_target`, `quality`), `inspection` (`uninspected`, `inspected`, `unavailable`), `use`, `ignore`, `approved_identity`, `gm_only`. Use/ignore traits require inspection. Approval as identity also requires inspection. |
| `locks` | Existing nonroot JSON Pointer paths, excluding the automatically managed `/revision`. Change only with user authorization; explicit instructions changing a locked value count. |
| `assumptions`, `gm_notes` | Shared public assumptions and private contextual notes. Keep inferred appearance in public identity/presentation, not solely in assumptions. |

Use empty strings/lists and null output requirements for genuinely unspecified fields. They validate structurally but can yield an incomplete brief. Fill only what the task needs. Reference records contain no fake paths to rendered examples. A user-supplied approval/inspection record should be verified in the current task before relying on it as evidence.

`identity_reference_ids` must refer to identity or edit-target references. Each asset also uses its subject's identity references. An edit target must be a reference with role `edit_target`; `intent: edit` requires a target. A public asset or subject cannot require a private reference. Mark the consuming asset/subject private instead of silently stripping an identity requirement.

## Compilation and readiness

`compile` defaults to `--audience player`; private subjects/assets are excluded. Selecting a hidden asset for that audience fails. `--audience gm` includes private assets; all `gm_notes` are still excluded because they are not visual instructions. The output is derived JSON, never the full source. It has source ID, revision, a SHA-256 of canonical source JSON, audience, and `briefs`.

Each brief contains its asset and subject IDs, public identity, presentation, art direction, image prompt, filtered inspected references, `unresolved_reference_ids`, `render_ready`, and concrete `readiness_issues`. Referenced but uninspected/unavailable images emit only their IDs as unresolved, not locators or use/ignore directives. Subject form plus head/body description or counted anatomy is needed for readiness. An empty starter therefore stays incomplete. Missing style details do not block a renderer that can choose them under the user's instructions.

`--text` requires exactly one selected visible asset, avoiding accidental concatenation of a set. It returns the prompt for a ready brief only. Readiness is an authoring prerequisite, not proof of an executed inspection or a successful render. Review prose disclosure and resolve image availability before rendering. The compiler does not parse secret meaning in public fields.

The content hash is `sha256(json.dumps(source, sort_keys=True, separators=(",", ":"), ensure_ascii=False))`; it identifies canonical content, not original file bytes. No generation, image editing, file download, Atlas import, or approval occurs during compilation.

## Controlled revisions

A change file has `expected_revision` and `changes`, an array of `{path, value}` replacements. Paths must already exist. Whole arrays/objects can be replaced, but overlapping change paths are rejected. The helper copies the source, checks the revision, applies replacements, compares locked values, protects the source identity, validates, and increments revision. It never overwrites an input or existing output.

`schema_version`, `spec_id`, `revision`, and lock definitions cannot be changed through this helper. Existing subject, asset, and reference IDs retain their array positions; existing assets cannot be rebound to another subject. New entries may be appended. Removal, reordering, or identity rebinding is a deliberate master edit: preserve/review lock pointers, increment revision, then validate. No extra approval is implied unless a specifically locked value needs an unresolved change.

The user can authorize a lock change through their request. Pass only the exact currently locked path to `--allow-locked`; authorization is not read from the change document. An ancestor replacement still has to preserve every unapproved descendant lock.

## Approval and image review record

Save review evidence outside the authoring source, for example:

```json
{
  "asset_id": "portrait-01",
  "subject_id": "subject-01",
  "source_revision": 1,
  "file": null,
  "brief": "ready",
  "image": "not_generated",
  "identity_reference": "not_requested",
  "atlas": "not_imported",
  "measurements": null,
  "visual_review": "not_run",
  "findings": []
}
```

Populate file/measurements only from an actual artifact. `inspect-image` reports width, height, format, alpha-channel presence, alpha extrema, and proportion of pixels with alpha below 255. It cannot prove edge quality, anatomical correctness, intended framing, likeness, or approval. Opaque alpha channels are reported as having no transparent pixels. No pixel transformations are performed.

`handoff` requires a public asset, a nonempty local `--approved-image` file, a structurally valid source, and a ready brief. It includes identity requirements and only user-approved identity references plus inspected style references. Other assets, private notes, edit-target locators, pose references, and unrelated reference records are excluded. Supplying `--approved-image` is an agent assertion of prior approval; the helper cannot verify consent or decode the image. The receiving workflow must inspect the image.

## Local verification

Run from the skill directory:

```sh
uv run --with 'jsonschema>=4.23,<5' --with 'pillow>=11,<13' python -m unittest discover -s tests -v
uv run --with 'ruff>=0.15,<1' ruff check scripts tests
uv run --with 'pyyaml>=6,<7' python /Users/farieds/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

The focused tests exercise duplicate/rebound IDs, stale revisions, ancestor lock changes, wardrobe variants, disclosure filtering, unavailable references, incomplete sources, output preservation, and actual alpha metadata using synthetic images. They do not generate images or establish Atlas acceptance.
