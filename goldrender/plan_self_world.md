# Visual Plan: "self and world hold each other upright"
## Rank 21 — Tier 3

### Palette
WARM_PARCHMENT=(244,240,232), REED=(182,160,130), REED_DARK=(140,118,88)
SELF_ROSE=(192,108,130), WORLD_TEAL=(92,146,148), GOLD=(206,166,88)
GOLD_LIGHT=(244,214,138), PURE_WHITE=(252,250,246)
VORTEX_CRIMSON=(154,46,60), FIELD_VIOLET=(120,104,168)
SKY_BLUE=(140,170,200), NIGHT_BG=(14,14,22), INK=(34,38,44)

### Scene breakdown

**Scene 1 — Two Bundles of Reeds (6s)**
- Background: parchment ground with warm golden halo
- Visual: Two arcs (cubic beziers) leaning toward each other from left and right
  - Left bundle: 8-10 thin line-segments fanning from (300,400) leaning right, defined as small angled lines
  - Right bundle: 8-10 thin lines from (980,400) leaning left
  - Where they meet at top-center (640,140), they prop each other up
  - Animation: reeds draw in from bottom using partial_polyline
  - Text banner bottom: "neither stands alone"
- Primitives: line() for individual reeds, bezier() for the overall arc shape

**Scene 2 — The Braid (6s)**
- Background: parchment with teal-rose dual halo
- Visual: Two vertical sine-wave strands interweaving
  - Rose strand (self): sine wave from (cx-40,100) to (cx-40,450)
  - Teal strand (world): sine wave from (cx+40,100) to (cx+40,450)
  - They cross at regular intervals — wave phase offset by π
  - Labels at bottom: "consciousness — nāma-rūpa"
  - Animation: strands grow upward using partial_polyline
- Primitives: line() for sine waves constructed from point lists

**Scene 3 — The Enacted World (6s)**
- Background: darker parchment with action-perception halo
- Visual: A large circle (cx,cy,150) with arrows indicating cycle
  - Top arc labelled "perception" — dotted arc
  - Bottom arc labelled "action" — dotted arc
  - Small eye at left, small hand at right
  - Central text: "the organism enacts its world"
  - Animation: circle draws as arc, arrows appear sequentially
- Primitives: arc() for circle, polygon() for arrows, ellipse() for eye/hand

**Scene 4 — Infinite Mirrors (6s)**
- Background: deep parchment with silver mirror sheen
- Visual: Two rounded rectangles facing each other
  - Left mirror at x=280 — labelled "self-model"
  - Right mirror at x=1000 — labelled "world-model"
  - Between them: recursively shrinking rectangles suggesting infinite regress
  - Connecting lines between them at multiple heights
  - Animation: mirrors appear, then recursive reflections fade in
- Primitives: rounded_rectangle() for mirrors, polygon() for regress, line() for connections

**Scene 5 — The Vortex (6s)**
- Background: dark background with crimson-vortex glow
- Visual: Centered spiral that tightens over time
  - Archimedean spiral constructed from point list
  - As t progresses, the spiral winds tighter (more turns, smaller inner radius)
  - Small particle dots orbit the spiral
  - Text: "grasping hardens the loop"
  - Animation: spiral draws from outside in
- Primitives: line() for spiral dots, ellipse() for particles

**Scene 6 — Loosening (6s)**
- Background: dark background softening to warm
- Visual: The same spiral but now expanding/unwinding
  - Spiral grows larger, spaces between turns widen
  - Gold light enters from top
  - Particles drift outward
  - Text: "the vortex becomes transparent"
  - Animation: spiral unwinds, light beam descends (lineglow)
- Primitives: line() for spiral, lineglow() for light beam

**Scene 7 — The Ground (6s)**
- Background: luminous violet-gold field
- Visual: Two small ripples on a vast still pond
  - Two ellipse-ripples expanding from left and right
  - They overlap in center without disturbing each other
  - The water surface is the only reality — the ripples are appearances
  - Text: "one field — two movements"
  - Animation: ripples expand from two points, cross
- Primitives: ellipse() rings with decreasing alpha for ripples

**Scene 8 — Closing Seal (6s)**
- Background: luminous pale field
- Visual: Two bundles now made of golden light
  - Same reed-arc shapes from Scene 1 but now luminous lines
  - They no longer lean — they float, parallel and vertical
  - Golden particles rise between them
  - Light source from below illuminates upward
  - Text: "self and world hold each other upright in light"
  - Animation: reeds transition from leaning to floating
- Primitives: lineglow() for luminous reeds, ellipse() for particles
