# Running Decisions Log — Seasonal QR

Append one entry per decision, most recent at the bottom. Never rewrite or delete a past entry; if a decision changes later, log the change as a new entry that references the old one.

## 2026-11-01 — Tile tree (voxel) proposed as v1 art direction (pending confirmation)
**Decision:** Build trees from the same tiles that become the QR, stored as slot clouds (voxel data). Smooth mesh trees become a later art pack using the same tile system.
**Why:** It makes the transformation literal and cohesive, replaces most Blender work with small data files, and gives contributors an easy path (MagicaVoxel → PR).
**Alternatives considered:** v1's smooth mesh tree dissolving while a separate tile grid assembles (two unrelated effects; heavy asset pipeline).

## 2026-11-01 — Every QR cell is a tile; tile budget follows QR version; input capped at v10/M
**Decision:** Tile count = (n + 8)² including the quiet zone. Trees store ≥ 4,225 slots in a seeded-shuffle order; use the first T and scale tiles by cbrt(total / T). Show a byte-based density meter.
**Why:** v1 assumed a fixed tile pool, but tile counts range from ~1,100 to 4,225+. Rendering the quiet zone as tiles keeps codes scannable on dark-mode pages.
**Alternatives considered:** A fixed pool with leftover tiles flying away; unlimited payload length.

## 2026-11-01 — Radial unfold mapping with finder patterns first
**Decision:** Map tree height to grid radius and azimuth to grid angle in chunked sorts; the three finder patterns land first; delay grows with radius; reverse = same mapping backwards.
**Why:** Deterministic, O(n log n), reads as intentional motion, and the QR becomes recognisable early.
**Alternatives considered:** v1's vortex with arbitrary targets (risk of chaotic crossing paths); optimal assignment (too slow for 4k tiles in the browser).

## 2026-11-01 — GPU-driven morph via per-instance attributes and one progress uniform
**Decision:** Start/end positions, colours and delays live in instanced attributes; GSAP animates `uProgress` and the camera; `useFrame` only handles ambient motion.
**Why:** Zero per-frame CPU work at 4k+ tiles; scrubbing and reverse for free; deterministic frames for video export and CI.
**Alternatives considered:** Updating instance matrices on the CPU in `useFrame` (v1).

## 2026-11-01 — Explicit scan-ready spec + CI decode matrix
**Decision:** Final state: orthographic, whole-pixel modules, tone mapping off, unlit, zero gaps, no post-processing or particles, dark on light. CI renders every payload × palette × version case, decodes with ZXing and jsQR, including a degraded copy.
**Why:** v1 made correctness "non-negotiable" without saying how. These are the specific renderer settings that break scanning.
**Alternatives considered:** Manual phone testing only.

## 2026-11-01 — Video export is the first post-MVP feature
**Decision:** Export the reveal as square and vertical video, recorded at a fixed timestep, holding the scannable final frame for ≥ 2 s.
**Why:** The animation is the product; a PNG is indistinguishable from any QR generator. The panel disagreed on MVP vs v1.0; chose v1.0 to keep the MVP lean, since the GPU morph makes it straightforward.
**Alternatives considered:** Video in the MVP (Product Skeptic); no video (v1).

## 2026-11-01 — One-page site; Vite suggested over Next.js
**Decision:** The landing page is the playground; docs live in the repo. Vite + React suggested for a static, client-only app (Next.js static export acceptable).
**Why:** Prove the core moment before building five routes; simpler for contributors to clone and run.
**Alternatives considered:** v1's five-route Next.js site.

## 2026-11-01 — Placeholder tree in code before any art
**Decision:** Phase 2 uses a code-generated cone tree to prove the morph and scanning at v2, v5 and v10 before the Sakura tree is drawn.
**Why:** Isolates the hardest risk without a Blender dependency.
**Alternatives considered:** Starting with the Sakura asset (v1 Phase 2).

## 2026-11-01 — Tile tree confirmed (resolves "Tile tree (voxel) proposed as v1 art direction")
**Decision:** Option A, trees built from the QR tiles, is the v1 art direction. Smooth mesh trees remain a possible later art pack.
**Why:** Gabriel confirmed it. Cohesive transformation, light asset pipeline, easy contributions.
**Alternatives considered:** Smooth dissolving tree (v1); prototyping both.

## 2026-11-01 — Goal: portfolio piece + open-source community project
**Decision:** Success = scan correctness, 30-second first use, a published case study + demo video, and a contribution ladder (palettes → presets → trees → code) with good-first-issues at launch. Contributed assets must be CC BY 4.0 or CC0.
**Why:** The portfolio needs polish and a clear write-up; the community needs a first contribution that takes minutes, with CI doing the correctness checks so maintainer load stays small.
**Alternatives considered:** Treating it as a possible product (would pull in accounts/monetisation, which serve neither goal).

## 2026-11-02 — Iteration 1 scope = plan §21 steps 1–3, built in parallel against pinned contracts
**Decision:** Iteration 1 delivers Phase 1 (pure QR engine, flat instanced grid under the scan-ready spec, Playwright decode matrix in CI) plus Phase 2's placeholder cone tree, radial unfold and GPU morph. Work was split three ways (pure modules / scene / tests + CI) with the interfaces fixed up front in `src/qr/types.ts`, `src/mapping/types.ts` and the app URL contract (`?text=…&t=end&seed=…`, `body[data-ready="true"]`).
**Why:** The three slices have no file overlap, and fixing the contracts first lets them proceed without waiting on each other. Proving tree → scannable QR is the hardest risk, so it comes before any art.
**Alternatives considered:** Phase 1 only (safer, but leaves the morph risk unproven); sequential build (slower, no benefit).

## 2026-11-02 — Iteration 2 scope = Phase 3 Sakura MVP, sakura tree generated in code
**Decision:** Iteration 2 delivers plan Phase 3: a code-generated sakura slot cloud (`sakuraSlotCloud`, same contract as the cone), platform and petals that are hidden in the scan-ready frame, "stamp, unfold, align" camera choreography on the one GSAP timeline, a density meter, PNG export beside SVG, and a Playwright test that decodes both exported files. Same three-way split with no file overlap (pure mapping + export test / scene + App / UI), with the export-link contract (`a[download="seasonal-qr.png"]`, `a[download="seasonal-qr.svg"]`, data: URLs) pinned up front.
**Why:** §21 step 4 says the Sakura tree comes after the morph is proven, which iteration 1 did. Generating the sakura in code keeps the MVP free of the MagicaVoxel import tool (Phase 5) while still being a real, recognisable tree.
**Alternatives considered:** Drawing the tree in MagicaVoxel now (needs the import tool first); seasons and video export (v1.0, Phase 4).

## 2026-11-02 — Sculpted Blender tree with tiles hidden inside (changes "Tile tree confirmed")
**Decision:** The tree at rest is a smooth, lit, sculpted sakura on a tiered diorama base, built procedurally in Blender (`npm run tree:build`, Blender needed only to rebuild) and shipped as `public/models/sakura.glb`. The QR tiles are hidden inside the trunk and canopy volumes (slot cloud sampled from the mesh into `public/trees/sakura.json`) and fly out on Reveal while the mesh dissolves. This iteration: tree + base only; pond, bridge, lantern and grass are later props.
**Why:** Gabriel reviewed the voxel sakura from the first half of iteration 2 against the motionsites "sakura-qr" reference and rejected it: a few thousand unlit cubes can only read as confetti, never as the sculpted diorama tree the project is meant to evoke. Hiding the tiles inside the mesh keeps the morph literal enough (the tiles do come out of the tree) while letting the rest state look like the reference.
**Alternatives considered:** Hybrid where the tiles are the blossoms drawn as lit blobs (more stylised than the reference); polishing the voxel look with lighting and smaller tiles (stays blocky). The contribution path for trees now needs Blender or any GLB plus a sampled slot cloud instead of MagicaVoxel; the import tool in Phase 5 should sample slots from a GLB.

## 2026-11-02 — Mosaic QR: lawn becomes the light modules, scene colours become the dark patches
**Decision:** The scan-ready QR is a mosaic of the diorama instead of black on white. Tiles for light modules and the quiet zone are hidden in the lawn and land in a pale grass tone; tiles for dark modules come from the tree and props and land in a deep version of their source colour (bark, magenta blossom, slate stone, pond blue). The landed grid always spans the whole 72-unit base top, with tiles scaling up as they land, so every payload length fills the lawn. The pairing runs as two radial unfolds, one per tone. The dark palette is as deep as ZXing needs: the first pass with mid pinks failed the direct decode, so blossoms land at about `#8c1f52`.
**Why:** Gabriel wanted the code to carry the art's colour scheme like the motionsites reference, and the whole grass patch used. Plan §5.7 allows tinted codes only when they pass the CI decode matrix, which they do.
**Alternatives considered:** Pink on white only (loses the lawn and props); three distinct blossom shades (too light for ZXing on the direct render).

## 2026-11-02 — Phase 4 in two iterations; seasons are data plus two asset files
**Decision:** Phase 4 starts with a season registry (`src/seasons/index.ts`: colours, base size, petal classes; assets at `public/models/<id>.glb` and `public/trees/<id>.json` under the sakura node and slot-class contract), a season picker and `?season=`, the CI decode matrix over every season with assets, an autumn maple diorama built from a shared Blender module, then video export and fragment-only share links. Summer and winter trees follow in the next iteration.
**Why:** Phone scan of the mosaic sakura code passed and CI is green, so the MVP is proven. Making seasons data-driven first means each new tree is only a registry entry and two generated files, which is the contribution path the plan wants. Video export is the first post-MVP feature by the earlier decision.
**Alternatives considered:** All four trees before any sharing features (too long without a shippable step); seeds as a visible feature (the tree is a fixed asset now, so the seed only jitters the unfold; parked).

## 2026-11-02 — Palette rule: dark module colours stay in one brightness band
**Decision:** Every season's `finalDark` colours must sit in a narrow luma band (min ≥ 38, spread ≤ 50 on a 0–255 scale) and below 40% of `finalLight`'s luma; a unit test enforces it and the Playwright matrix remains the real gate.
**Why:** Autumn's first palette rendered correctly but ZXing read the amber modules as light inside large dark areas, because its local threshold is set by the surrounding near-black bark modules. Decoders threshold locally, so the spread between dark colours matters as much as dark-versus-light contrast.
**Alternatives considered:** Only the Playwright matrix (slow feedback for palette contributors); one dark colour per season (loses the mosaic).
