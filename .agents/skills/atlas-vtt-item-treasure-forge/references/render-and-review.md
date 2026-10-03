# Rendering and inspection

Load the current `imagegen` skill for requested raster generation/editing. Use the actual inspected references and base image through its supported input mechanism. Do not claim a reference was delivered solely because its locator appears in JSON. Inspect local images before editing; recover unavailable targets before dependent work. Source validation supplies no image evidence.

For a loot close-up, prioritize:

- One readable silhouette and the requested count. Keep the whole item visible when requested, including blade tip, grip, handles, clasps, stopper, and feet.
- Coherent construction. Guards attach to blades, handles attach to vessels, stitching follows seams, and closures fit their openings. Materials have distinct surfaces and plausible joints unless the chosen design is deliberately impossible.
- Recognizable identity marks. Give a notch, inset, repair, enamel panel, or sculpted motif a precise location and count. Keep lighting from obscuring it.
- Deliberate display composition. Viewpoint shows required faces and markings; shadows, margins, overlap, and background serve the intended reveal. A group display must preserve item separation and count.

For coherent sets, compare shared light direction, rendering, background, and material response in actual images. A palette in every prompt does not prove consistency. Reuse selected identity/style references where available. An image edit must compare unchanged identity details with its base; source locks protect data, not pixels.

## Lettering

Use approved text exactly. Text directly supplied by the user, or explicit authority to choose final wording, suffices without another approval round. Do not silently rewrite names, punctuation, accents, or line breaks. Honor the user's handling choice:

- `exact_composition`: generate the item with a suitable unlettered region, then compose the retained text with a deterministic text-capable tool appropriate to the output. Check the actual text and placement after composition. Perspective, curved surfaces, or engraving may require deliberate layout work; a plan does not execute it. If the environment cannot support the requested composition, explain the limit with the editable plan.
- `render_and_verify`: include text in the image request, then read and compare every character in the result. OCR can assist but is not conclusive. Report a mismatch and repair through the requested workflow; never promise perfect lettering from the prompt.
- `decorative`: illustrate the specified nonliteral marks. If the user requires an exact symbol or supplied emblem, reuse the inspected reference and inspect the result; route standalone emblem design to Heraldry & Symbol Forge.

Do not turn an item's short inscription into a written handout. Route a discovered letter, plaque whose primary purpose is prose, journal page, or document clue to Handout Forge.

## Review evidence

Use normal image viewing for visual review. Measure the file's dimensions; for transparent requests measure the alpha channel and inspect edges on contrasting backgrounds. An alpha-capable format, opaque alpha channel, or painted checkerboard does not establish a clean transparent cutout. Preserve transparency on edits unless requested otherwise.

Record actual results separately from source targets. This unpopulated record is an example, not executed evidence:

```json
{
  "asset_id": "saber-closeup",
  "item_ids": ["tideglass-saber"],
  "source_revision": 1,
  "file": null,
  "brief": "ready",
  "image": "not_generated",
  "lettering": "pending",
  "approval": "not_requested",
  "atlas": "not_imported",
  "actual_width_px": null,
  "actual_height_px": null,
  "alpha_review": "not_run",
  "visual_findings": []
}
```

Populate only observed file data. Review does not confer user approval as campaign canon. Display the saved illustration inline when useful and state unresolved requirements plainly.
