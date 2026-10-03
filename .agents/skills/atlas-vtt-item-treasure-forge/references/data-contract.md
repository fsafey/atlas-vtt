# Item illustration source contract

The source is authoring JSON, not an Atlas asset or scene. `schema_version` is 1; `revision` starts at 1. `spec_id`, `item_id`, `asset_id`, `reference_id`, and `inscription_id` are stable lowercase IDs. Keep existing array order stable because locks use JSON Pointer paths.

| Field | Meaning |
| --- | --- |
| `items` | Each object's public name, kind, `appearance`, inscriptions, `gm_only`, and private `gm_notes`. Kinds classify artwork, not mechanics. |
| `appearance` | Shape and proportions; arrays of materials, colors, construction details, distinctive marks, and wear. These fields define visible identity. |
| `inscriptions` | Stable ID, exact `text`, visible placement, and handling: `exact_composition`, `render_and_verify`, or `decorative`. Preserve punctuation, case, Unicode, and line breaks for exact text. |
| `assets` | A distinct image ID/title, included `item_ids`, `intent` (`generate` or `edit`), presentation, reference IDs, nullable `edit_target_ref`, visual constraints, and disclosure. Multiple items in one asset mean a group display, not separate image files. |
| `presentation` | Viewpoint, arrangement, framing, background, and output requests. An arrangement describes object count, placement, and overlap where relevant. |
| `background` | `unspecified`, `solid`, `environment`, or `transparent`, plus a concrete description. |
| `output` | Nullable width/height in pixels and nullable `[width,height]` aspect ratio. Supply both dimensions together; explicit dimensions must match the ratio. Values are requests, not observed output. |
| `art_direction` | Shared medium, rendering treatment, palette, lighting, and mood for the current set. Distinct styles can use separate sources. |
| `references` | Actual locator, role (`identity`, `style`, `material`, `composition`, `edit_target`), inspection status, traits to use/ignore, and `gm_only`. Uninspected or unavailable references cannot assert visual observations. |
| `locks` | Existing nonroot JSON Pointer paths into authoring values. Source identity, revision, schema version, and lock definitions are managed separately. |
| `assumptions`, `gm_notes` | Public design choices and private context. Put render-critical choices in appearance/presentation as well. |

Blank appearance values keep sparse input editable. `render_ready` requires shape and materials for every included item, viewpoint and arrangement, and inspected required references. Readiness is a source assertion, not proof of visual inspection, reference delivery to a renderer, or generated quality. An edit requires a role-matched edit target; inspection and actual image availability must be checked at use time.

A public asset cannot require private items or references. Mark the consuming asset private when it needs them. A hidden inscription belongs on a private item/asset variant, not in the public object's prose. Filtering never detects the semantic secrecy of text put in public fields.

## Derived briefs

`compile` defaults to `--audience player`, excludes private assets, and errors on a specifically selected absent/private asset. `--audience gm` includes private artwork while still excluding all `gm_notes`. Each brief contains only its used items and inspected references, presentation, art direction, constraints, lettering plan, image prompt, and readiness issues. Uninspected references emit only unresolved IDs, without locators or directives. Unused reference records are absent.

Exact composition plans preserve text outside the image prompt. The prompt reserves an unlettered surface at the stated placement. `render_and_verify` includes the requested text in the prompt and a pending inspection plan. Neither approach claims composition or inspection occurred. Decorative marks are visual directions without a literal spelling promise.

The content hash is SHA-256 of `json.dumps(source, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`. It identifies canonical source content, not original bytes. Compilation marks images `not_generated` and Atlas `not_imported`; it does not execute a provider, compose text, fetch references, or verify dimensions/alpha. `--text` requires exactly one ready visible asset; use JSON output when a set or lettering plan must travel with the prompt.

## Focused revisions

A change has `expected_revision` and nonempty `changes` containing `{path,value}` replacements for existing paths. Overlapping paths, managed metadata edits, stale revisions, ID changes, record removal/reordering, and rebinding an existing asset to different items are rejected. New records may be appended. The helper copies the source, applies replacements, compares locked values including descendant locks of ancestor replacements, increments revision, and validates.

Explicit user instructions that change a locked value authorize that value. Supply the exact existing path with `--allow-locked`; the change file cannot grant itself permission. Preserve other locks. Removal, identity rebinding, or lock definition changes require a deliberate master edit with lock-pointer review and a revision increment. This is an editing distinction, not an extra user approval flow.

All file outputs use exclusive creation and refuse existing files. Resume from the saved revision and artifact record; repeated commands do not overwrite approved work. Use a different output path for a deliberate new derivative.

## Focused local checks

Run from this skill's folder:

```sh
uv run --with 'jsonschema>=4.23,<5' python -m unittest discover -s tests -v
uv run --with 'ruff>=0.15,<1' ruff check scripts tests
uv run --with 'mypy>=1.19,<2' --with 'jsonschema>=4.23,<5' mypy --ignore-missing-imports scripts/item_spec.py
uv run --with 'pyyaml>=6,<7' python /Users/farieds/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

These checks cover source invariants and CLI behavior. They do not establish generated imagery, exact text composition, transparency, installation discovery, or Atlas acceptance.
