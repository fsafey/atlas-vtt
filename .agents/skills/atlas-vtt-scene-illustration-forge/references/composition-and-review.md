# Reveal composition and visual review

Use this reference for composition choices and image inspection. The user's explicit art direction takes precedence over suggested defaults.

## Location reveals

A reveal gives the viewer a place to look and a sense of standing somewhere. Connect the camera position to the location: from a doorway into a hall, across a valley toward a gate, beneath a tower, or above a plaza. State the focal landmark and how it separates from its surroundings. Foreground framing, overlapping planes, scale cues, value contrast, and atmospheric distance can create depth without requiring all of them in every image.

For interiors, check door/window placement, readable room depth, ceiling perspective, furniture scale, and a plausible source of light. An establishing view can prioritize a bar, stair, altar, workshop, or window rather than an exhaustive inventory. Preserve explicit requests for unusual perspective or stylized architecture.

For landscapes and architecture, establish the major silhouette and relation to terrain first. A recurring tower, bridge, gate, skyline, or mountain arrangement anchors coherent variants. Keep those relations explicit where later viewpoints or lighting changes could cause drift. An illustrated reveal is not evidence of navigable map geometry.

## Dramatic moments

State one visible moment in plain terms, then participant placement, action direction, and the focal point. Separate focal action from supporting atmosphere. Review contact, gestures, gaze, relative scale, and occlusion so the action remains understandable. Use approved character identity references when recognizable figures recur; do not invent a new face or costume from a filename. If participant identity is the primary deliverable, route it to Portrait Forge.

Describe light direction, color, and visible sources where they matter. Moonlight plus firelight can coexist if their different roles are clear. Weather and particles should support the subject instead of obscuring a required landmark. A scene can be calm, schematic, surreal, monochrome, or graphic when requested; cinematic realism is an option, not a compulsory style.

## Coherent variants and narrow edits

For dawn/night, summer/winter, intact/damaged, or alternate-view sets, keep the shared identity stable and describe per-image differences explicitly. A new view can expose previously unseen structure; do not claim an existing reference proves what it cannot show. Record new inferred details as assumptions before accepting them into the source.

For a lighting-only edit, preserve camera, framing, silhouette, recurring landmarks, figures, material identity, and architecture unless specifically changed. Compare the actual base and result. A source lock or a prompt saying preserve does not prove those pixels or relations survived. When the base is missing, a fresh-generation variant has weaker continuity than an actual edit; report that limitation.

## Review evidence

Check the actual artifact against these applicable requirements:

| Requirement | Evidence to record |
| --- | --- |
| Identity and layout | Recurring landmarks, architecture, materials, and approved participant traits visible in the image. Compare against inspected references and prior variants. |
| Composition | Requested camera and frame, clear focal hierarchy, depth, scale, crop margins, and requested visible action. |
| Atmosphere and light | Requested time/weather/mood, understandable light sources and shadows, required details readable through fog or particles. |
| Disclosure | No private variant details, secret landmarks, unintended text, or private reference material baked into the player image. |
| Lettering | Exact requested words, spelling, and placement; report uncertainty or mismatch rather than approving by prompt alone. |
| Output geometry | Actual width, height, aspect ratio, and any crop. Requested dimensions are targets, not a verified output. |
| Transparency | Actual alpha extrema, proportion of pixels below alpha 255, and visually clean edges when transparency is requested. Opaque RGBA files and painted checkerboards do not pass. |
| Set or edit continuity | Compare recurring identity and unrequested features across actual images, then report drift. |

Use image viewing for visual findings. If metadata tools are unavailable, a read-only Pillow check through `uv run --with 'pillow>=11,<13' python` can record width/height, format, and alpha extrema. Count pixels with alpha below 255 when transparency is a requirement, and visually inspect halo/fringe edges. Do not claim those numbers establish correct silhouettes or visual quality.

Mark an image `reviewed` only after applicable checks were performed and findings recorded. Report unmet requirements clearly; keep approval as a campaign reference and Atlas presentation as separate assertions.
