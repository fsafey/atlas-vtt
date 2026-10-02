# Art direction and inspiration

These are authored design heuristics and presets, not claims that any specific generator guarantees an outcome. They are intended to produce distinctive places with useful map structure, not a generic “epic fantasy” texture.

## What makes the supplied reference useful

The user-provided image shows an overhead regional composition with obliquely drawn mountains and buildings. A dominant fortified settlement anchors the upper portion. Different woodland, water and rock silhouettes organize the lower landscape. Fine linework and muted washes provide detail without making every patch equally prominent. Numbered hexes, text and interface pins sit over that artwork.

Borrow the separation of geographic masses, landmark silhouettes and fine detail. Do not reproduce the cursor, pins, cropped header, names, or original layout as accidental artifacts. The original image is not included in this package; the example preserves its broad observed traits as a text reference.

## The curation sequence

**First, make a place.** What caused it to exist? What one visible object makes it recognizable? What can a player infer before being told the lore?

**Second, make geography matter.** A fortified bridge is valuable because it joins routes across an obstacle. A forest can hide a shortcut, divide a valley, or encroach on a settlement. The physical arrangement should support a choice, not merely display a checklist of objects.

**Third, organize the image.** Use one dominant anchor, a few supporting destinations and ambient terrain. Regional detail can be dense while the main landforms remain simple. In tactical work, busy detail belongs at edges and cover positions rather than every traversable cell.

**Fourth, tie the visual language together.** Repeat materials, construction logic or motifs in a controlled way. A bronze astronomical ring can echo in old milestone carvings without turning every building into an observatory. A single warm marsh can contrast with cool hills without adding a dozen unrelated magical color zones.

**Finally, remove accidental noise.** Delete meaningless scattered icons, redundant labels, competing light effects and decorations that erase movement paths. Keep the details that establish identity or help play.

## Five preset starting points

A preset is a shortcut for the authoring agent. The canonical `style` fields must still spell out its actual properties; the compiler does not expand preset names behind the scenes.

| Preset | Best starting use | Visual recipe | Protect against |
|---|---|---|---|
| `illustrated_adventure_atlas` | Regional exploration | Fine ink; muted watercolor; pictorial relief; miniature architecture; atmospheric but legible geographic masses | A camera horizon, identical tree stamps, mountains covering all paths |
| `painterly_tactical` | Outdoor encounters and complexes | True top-down geometry; painted local material texture; crisp walls and banks; restrained shadows | Isometric drift, unwalkable floors, hidden doors, excessive bloom |
| `warm_ink_encounter` | Taverns, villages, woodland encounters | Expressive hand-inked edges; light color washes; warm materials; selective charming props | Overdecorated floors, arbitrary oversized furniture, lost scale |
| `architectural_dungeon` | Ruins, temples, interiors | Orthographic floor plan; decisive wall cuts; limited palette; subtle wear; clear openings | Decorative black areas confused with holes, disconnected stairs, sealed corridors |
| `mythic_cartographic` | Unusual worlds or cosmological regions | Symbolic but consistent terrain; one strong impossible premise; a disciplined motif/palette system | Random unrelated wonders and physically incoherent routes not explained by the premise |

None of these presets is an instruction to clone a particular artist. The user's cited libraries are quality and curation references; translate that intent into concrete, controllable properties.

## Inspiration questions that earn their place

| Decision | Productive question | Example alternatives |
|---|---|---|
| Signature silhouette | What would a traveler recognize from far away? | A city inside a petrified antler crown / a monastery between stone needles / a ring fortress around a black lake |
| Geography as a choice | What route decision should matter? | Exposed bridge versus hidden ford / short glass forest route versus river detour / high safe pass versus flooded low road |
| Evidence of history | What shows that this place has changed? | A road swallowed by roots / an old shoreline above today's town / a broken aqueduct reused as a market |
| Tone | What should players feel on first inspection? | Beautiful but unsafe / inhabited and worth defending / abandoned yet still functioning |
| Detail priority | Which three things must survive at thumbnail size? | Ring citadel / split river / three monoliths |
| Practical use | What must remain readable during play? | Door thresholds / two-cell corridors / alternate crossings / settlement approaches |

Do not ask all of these automatically. Choose only the unresolved decisions that change the map.

## A concrete content recipe

Weak: “An epic magical castle, extremely detailed, 8K masterpiece.”

Stronger: “One compact limestone city on three stepped defensive terraces. A single tilted bronze astronomical ring is its highest and most recognizable feature. One south approach descends to a stone bridge. Fine ink contours, slate-blue water, pale stone, gray-green vegetation, no competing luminous landmarks.”

The stronger version specifies identity, count, hierarchy, connection, material and palette. It is editable one property at a time. Pixel resolution is an export concern, not a style adjective.

## Scale and density

A forest entity is one forest mass, not a promise to count every tree. A quantity of three spires is a count requirement for three visible spires. When each spire needs a separate history, silhouette and location, make three named entities.

Avoid requiring every regional building to contain battlemap-level furniture. Use an original regional landmark as the reference for a separate local map when needed, with a newly authored floor plan and scale. A zoomed-in generation does not automatically recover a geometrically consistent interior from a pictorial icon.

## Geography and tactical review

Treat these as review questions, not automatic geographic proofs: do rivers visibly join their outlets? Are crossings actually on the watercourse? Do roads meet gates? Can a path climb the drawn cliff? Are walls distinct from shadows? Are stairs and doors physically connected? Does foliage hide required traversable space?

When geography intentionally breaks ordinary logic, name the exception. “This river climbs because the floating reservoir draws it uphill” is a deliberate fantasy premise; an unexplained uphill river is an unresolved inconsistency.
