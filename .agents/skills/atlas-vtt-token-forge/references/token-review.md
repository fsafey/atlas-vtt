# Token presentation and review

Choose treatment by tabletop use. Retain the user's art direction; these criteria do not prescribe a campaign style.

| Kind | Composition | Border and background |
| --- | --- | --- |
| `portrait_circle` | Square source; face/head and recognizable upper clothing inside the circular safe area. Protect ears, horns, hair, and the requested identifying equipment from the ring/crop. | Either an Atlas ring over unbordered art, or a baked circular border with transparent outer corners. A borderless portrait may use a transparent circle. |
| `top_down` | Orthographic overhead figure; clear head/body orientation and deliberate forward direction. Keep extremities and weapons inside the canvas. Avoid horizon lines and isometric camera tilt. | Default transparent canvas without a border. Retain an explicitly requested base, border, or shadow. Separate silhouette from the map through the subject's contrast and edge treatment. |
| `creature_cutout` | Whole recognizable creature; specify side, three-quarter, or overhead view. Preserve anatomy counts and all requested wings, tails, horns, feet, and carried objects. | Default transparent canvas without a border. Avoid background fragments, floor discs, and shadows unless requested. Review deliberate opaque bases or borders against the intended use. |

A large canvas with a tiny centered subject can become unreadable when Atlas fits its longest edge. Balance margin with usable scale. `safe_margin_percent` is a requested inset from canvas edges, not proof that the render obeyed it or a calculated circular crop guarantee. A circular crop can remove corners even when an ordinary inset is respected.

At full size inspect anatomy, identity, material/color continuity, unexpected objects or text, and crop safety. View against light and dark backgrounds when alpha edges matter; check for halos, missing internal gaps, fringing, and semiopaque scenery. Metadata alone cannot prove a clean cutout. Nontransparent bounds include any painted shadows or stray pixels, not a semantic subject outline.

Then inspect at each specified tabletop display size, often 64 and 128 pixels for a starting comparison. These are chosen review targets, not Atlas requirements or guaranteed screen sizes. Use an image viewer's actual size/zoom controls. Record the sizes actually reviewed. Check that the intended subject and direction can be recognized, the primary colors remain distinct, and identifying features survive. Do not reject natural loss of tiny facial detail if the user only needs a recognizable silhouette; preserve the most useful identity cues for the requested view.

For a set compare visual weight, silhouette scale, shared colors, border width, lighting, and identity markers. For a narrow revision compare the unrequested face/head, anatomy, clothing, equipment, viewpoint, pose, alpha, and crop against the inspected approved base. If a mismatch materially impairs use, perform a focused edit within the request and review it again. Preserve earlier approved files.

Keep the review record beside the source and images:

```json
{
  "asset_id": "token-01",
  "subject_id": "subject-01",
  "source_revision": 1,
  "source_sha256": null,
  "brief": "incomplete",
  "image": "not_generated",
  "file": null,
  "measurements": null,
  "visual_review": "not_run",
  "tabletop_review": "not_run",
  "reviewed_display_sizes_px": [],
  "findings": [],
  "atlas": "not_imported"
}
```

Populate hashes, files, measurements, and findings only from actual work. Identity approval is a user decision carried from trusted task context; a visual quality review does not invent approval.
