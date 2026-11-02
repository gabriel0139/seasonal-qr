# Seasonal QR — Open-Source Project Plan (v2)

> A desktop-first, browser-based creative experiment that turns a seasonal 3D tree into a real, scannable QR code.

**Working name:** Seasonal QR
**Repository:** `seasonal-qr`
**Project type:** Open-source creative coding project
**Initial platform:** Desktop/laptop browsers
**Architecture:** Fully client-side static site; no account or backend
**Status:** v2.1 plan, 2026-11-01 (art direction and goal confirmed) · supersedes v1

---

## What changed from v1

| # | Change | Why |
|---|---|---|
| 1 | **The tree is built from the QR tiles themselves** (a voxel "tile tree"), proposed as the v1 art direction | The transformation becomes literal, not an illusion of one asset dissolving while another appears. It also replaces most Blender work with small data files |
| 2 | **Tile budget system**: tile count follows the QR version, with a payload cap and a live density meter | v1 assumed a fixed tile pool, but a 50-character URL and a 200-character one need very different numbers of tiles |
| 3 | **Radial "unfold" mapping** from tree positions to QR cells, with finder patterns landing first | Chaotic tile paths are the biggest risk to the animation looking intentional. This mapping is cheap and deterministic |
| 4 | **Motion runs on the GPU**, driven by one progress value | Thousands of instances move with zero per-frame CPU work; the timeline becomes scrubbable and reversible for free, and video export becomes deterministic |
| 5 | **Concrete scan-ready spec**: tone mapping off, zero-gap tiles, whole-pixel modules, quiet zone rendered as tiles | v1 said "remove effects". These are the specific things that silently break scanning in a 3D renderer |
| 6 | **Automated scan tests in CI** across payloads × palettes, including camera-like degradation | Correctness is "non-negotiable" in v1, so it must be enforced by tests, not good intentions |
| 7 | **Video export of the reveal** (ending on a scannable QR) | The animation is the product. A PNG looks like any other QR code; a 6-second clip is what gets shared |
| 8 | **Single-page site for v1**: the landing page *is* the playground | v1 planned five routes plus a docs site before the core moment was proven |
| 9 | **Placeholder tree generated in code** before any art assets | Proves the hardest risk (tree → scannable QR) with no Blender dependency |
| 10 | Vite suggested over Next.js | It's a static, client-only app; simpler for contributors |

The v1 → v2 review panel is in §19.

---

## 0. Goal and success measures

**Goal (decided 2026-11-01): portfolio piece + open-source community project.** Polish and a strong write-up serve the portfolio; a low-barrier contribution path serves the community. Anything that serves neither (accounts, monetisation, invasive analytics) stays out.

v1.0 success measures:

- **Correctness:** the reveal ends in a QR that decodes on every CI test case and on three real phones.
- **First use:** a first-time visitor gets from landing to a scanned QR in under 30 seconds.
- **Portfolio:** a published case study (the problem, tile budget, radial unfold, scan-ready spec, and what didn't work), a 15–30 s demo video, and a README GIF.
- **Community:** a contribution ladder (§8.1), at least five labelled good-first-issues at launch, and at least one outside palette or tree merged after launch.
- **Sharing:** people post exported videos. Track this lightly via GitHub stars and mentions.

---

## 1. Vision and user journey

A visitor types a URL or text, picks a season, and watches a small seasonal tree, built from tiles, unfold itself into a working QR code on its platform. Then they scan it, download it, or export the whole reveal as a short video.

**Core journey (v2):**

1. Land on the site: a live seasonal tree is already on screen, with an input box beside it.
2. Type a URL or text. A density meter shows how big the QR will be.
3. Pick Spring, Summer, Autumn, Winter or Random.
4. Press **Reveal**. The tree unfolds into the QR (~5 s).
5. Scan it from the screen, or download PNG/SVG, or **export the reveal as a video**.
6. Press **Grow back** to reverse.

**Product principles (from v1, still valid):** genuine encoder output; the final QR must be easy to scan; themes are data-driven; everything runs locally; desktop first; open to community trees and palettes.

---

## 2. Art direction — decided: tile tree (Option A)

| | **Option A — Tile tree (recommended)** | Option B — Smooth tree (v1) |
|---|---|---|
| Look | A stylised tree built from small rounded tiles/voxels, diorama-like | A sculpted low-poly tree with foliage clusters |
| Transformation | Literal: the same tiles move from tree to QR | Illusion: the mesh dissolves while separate tiles assemble |
| Asset work | Small voxel data files (MagicaVoxel or Blender voxelised) | Full Blender modelling, GLB optimisation, foliage materials |
| Community contributions | Easy: draw a tree in a free voxel editor, open a PR | Hard: Blender skills plus export pipeline |
| Risk | Must look charming, not like Minecraft | Transformation can look like two unrelated effects |

**Decided 2026-11-01: Option A.** Option B stays a possible later art pack.

If Option B is added later, it still uses the same tile system. Sample the tiles' start positions on the tree's surface (three.js `MeshSurfaceSampler`) and reveal them with a dissolve shader, so the tiles appear to peel off the tree. That makes a good later "art pack".

Seasonal palettes from v1 carry over unchanged (Sakura, leafy summer tree/willow, Japanese maple, snowy pine).

---

## 3. The tile system

### 3.1 Every QR cell is a tile

The final state is a full square of tiles: **dark modules** raised and dark, **light modules and the quiet zone** flat and light. Tile count = `(n + 8)²`, where `n = 4 × version + 17` and the `+ 8` is a four-module quiet zone on each side.

| QR version | Grid (n×n) | With quiet zone | Tiles | Byte capacity at EC level M (approx.) |
|---|---|---|---|---|
| 2 | 25 × 25 | 33 × 33 | 1,089 | ~26 bytes |
| 3 | 29 × 29 | 37 × 37 | 1,369 | ~42 bytes |
| 4 | 33 × 33 | 41 × 41 | 1,681 | ~62 bytes |
| 5 | 37 × 37 | 45 × 45 | 2,025 | ~84 bytes |
| 6 | 41 × 41 | 49 × 49 | 2,401 | ~106 bytes |
| 10 | 57 × 57 | 65 × 65 | 4,225 | ~213 bytes |

A typical URL lands at version 3–5. **Cap input at version 10** at EC level M, and show a live meter ("Short · Medium · Dense"). Longer content makes a denser tree and a harder-to-scan code.

Rendering the quiet zone as light tiles matters: if it relied on the page background, the QR would fail on a dark-mode page.

### 3.2 The tree as a slot cloud

Each tree is stored as an ordered list of **slots** (position plus palette index) with at least 4,225 entries, enough for version 10.

- **Order the slots with a fixed seeded shuffle**, so any prefix covers the whole silhouette evenly.
- For a payload needing `T` tiles, use the first `T` slots, and scale tiles by `cbrt(totalSlots / T)` so the tree looks equally full at every payload length.
- Seasonal particles (petals, leaves, snow) are separate instances and are never part of the QR.

### 3.3 Tree → QR mapping: radial unfold

This is what makes the motion read as intentional rather than random.

1. **Finder patterns first:** the three 7×7 finder patterns (147 cells) take slots from the top of the canopy. They land first, so the code is recognisable as a QR early.
2. **Everything else unfolds outward:** low parts of the tree (trunk base) go to the centre of the grid; higher parts go further out. Within each band, match angle around the trunk to angle around the grid centre.
3. **Timing by radius:** each tile's delay grows with its grid radius, so a wave travels outward from the trunk. Add a small seeded jitter and a slight angular swirl for organic motion.
4. **Reverse is free:** "Grow back" is the same mapping with progress running from 1 to 0.

```ts
// slots: tree slots (first T, finder group removed) with height h and azimuth theta
// cells: QR cells (finder cells removed) with radius r and angle phi from grid centre
const s = [...slots].sort((a, b) => a.h - b.h);
const g = [...cells].sort((a, b) => a.r - b.r);
const pairs: [Slot, Cell][] = [];
for (let i = 0; i < g.length; i += CHUNK) {          // CHUNK ≈ one ring of cells
  const sChunk = s.slice(i, i + CHUNK).sort((a, b) => a.theta - b.theta);
  const gChunk = g.slice(i, i + CHUNK).sort((a, b) => a.phi - b.phi);
  sChunk.forEach((slot, j) => pairs.push([slot, gChunk[j]]));
}
// delay = finderGroup ? 0 : baseDelay + r * waveSpeed + seededJitter(slot.id)
```

This is O(n log n) and deterministic: the same seed gives the same motion every time.

### 3.4 Colour

Each tile carries a start colour (its tree palette colour) and an end colour (dark or light module). The colour blends as the tile lands. Assign trunk and branch tiles to dark modules where possible, so less colour change happens mid-flight.

---

## 4. The signature animation: "settle, unfold, stamp, align"

Target ~5 s; reduced-motion version ~0.3 s.

| Stage | Time | What happens |
|---|---|---|
| **1. Settle** | 0.0–0.6 s | Wind and particles calm; a light sweep crosses the platform |
| **2. Stamp** | 0.6–1.4 s | The three finder-pattern groups lift off the canopy and drop into their corners, like three stamps |
| **3. Unfold** | 1.4–3.6 s | The rest of the tree melts down from the trunk and spreads across the platform as a radial wave; seasonal particles trail and fade |
| **4. Align** | 3.6–4.6 s | The camera rises to a true top-down view; tiles settle with a small spring overshoot; dark modules rise, light modules flatten |
| **5. Scan-ready** | 4.6–5.2 s | Switch to the scan-ready state (§5); show **Scan · Download · Export video** |

**Reverse ("Grow back"):** the same timeline backwards, with wind and particles resuming at the end.

### 4.1 Implementation: GPU-driven morph

- One `InstancedMesh` for all tiles. Per-instance attributes: `aStart`, `aEnd`, `aDelay`, `aStartColor`, `aEndColor`.
- A custom vertex/fragment shader (or an extended standard material) interpolates position and colour from a single uniform, `uProgress`, using each tile's delay and an easing curve.
- **GSAP owns `uProgress` and the camera**, on one timeline. Scrubbing, reversing and pausing come for free.
- `useFrame` only drives ambient things (wind, particles), never per-tile transforms.
- Debug controls: a timeline scrub slider, plus a `?t=end` URL flag that jumps straight to the final state (used by the CI tests).
- Reduced motion: a short crossfade from tree to the flat QR.

---

## 5. Scan-ready final state (exact spec)

Apply every one of these in the final state:

1. **Orthographic camera**, exactly top-down, framing the `n + 8` modules.
2. **Whole device pixels per module:** size the frustum so each module is a whole number of device pixels (accounting for `devicePixelRatio`); letterbox the rest with the light quiet-zone colour.
3. **Tone mapping off** for final materials. React Three Fiber's default tone mapping shifts colours and lowers contrast; use `toneMapped={false}` on the tile material, or `<Canvas flat>`.
4. **Unlit colours** for final tiles: no lighting, shadows, bevels, gradients or textures.
5. **Zero gaps** between tiles, so adjacent dark modules merge into solid blocks. Gaps create light grid lines that some decoders trip on.
6. **No post-processing, particles or motion blur** in the final frame.
7. **Dark on light only** by default. Inverted codes fail on some scanners.
8. **Palette contrast:** each palette's `finalDark` and `finalLight` must pass the CI decode tests (§6); seasonal tints are fine only if they pass.
9. A conventional flat SVG/PNG is always available as a fallback.

---

## 6. QR correctness and testing

### 6.1 Encoder

Use `node-qrcode` (`qrcode` on npm). `QRCode.create(text, { errorCorrectionLevel: 'M' })` returns the module matrix, version and error-correction level. Keep the QR engine a pure module with no Three.js imports.

Input handling: UTF-8 byte mode; the density meter counts **bytes**, not characters (emoji and many non-Latin characters take several bytes each).

### 6.2 Automated scan tests (CI)

For every combination of **payload** (short URL, long URL near the cap, non-Latin text, emoji) × **palette** (every palette of every season) × **QR version boundary**:

1. Open the playground in Playwright (headless Chromium with software WebGL) using `?t=end`.
2. Screenshot the canvas at the reference size.
3. Decode with **two independent decoders** (ZXing JS and jsQR); both must return the exact payload.
4. Repeat on a **degraded copy** (downscale 50%, 1 px blur, JPEG quality 60) to approximate a phone camera.
5. Also decode the exported PNG and SVG and, once video export exists, the video's final frame.

A palette that fails any case can't be merged.

### 6.3 Real-phone checks (each release)

iPhone camera app, Android camera/Google Lens and one third-party scanner, scanning from a laptop screen at a normal distance, and from the exported video played on a second screen.

---

## 7. Seasons, palettes and seeds

v1's theme configuration stays, with these additions per palette: `finalDark`, `finalLight`, `quietZone`, and the slot-cloud file for the tree.

- Curated palettes per season (e.g. Traditional Sakura, Sunset Sakura, Lavender Spring).
- **Seeded randomness** drives the slot shuffle, jitter, particle layout and palette pick. The same seed always gives the same design.
- **The QR content never depends on the seed or theme.**

---

## 8. Asset pipeline (Option A)

1. **Draw** the tree in **MagicaVoxel** (free voxel editor), or model it in Blender and voxelise it.
2. **Convert** to a slot cloud (positions plus palette indices, ≥ 4,225 slots) with a small repo script; three.js ships a `.vox` loader to build on.
3. **Store** each tree as a compact binary or JSON file in `public/trees/`; total size should be tens of KB, not MB.
4. **Platform and props** stay simple meshes (GLB, optimised with glTF Transform).

**Contribution path:** "Draw a tree in MagicaVoxel → run `npm run tree:import` → open a PR with an asset-manifest entry." The CI scan tests then check it automatically.

### 8.1 Contribution ladder

Order the ways to contribute from easiest to hardest, so newcomers have a first step that takes minutes:

1. **Palettes:** a JSON file. CI runs the full decode matrix on it automatically, so maintainers don't hand-check contrast. Ideal good-first-issues.
2. **Particle and wind presets:** small config files.
3. **Trees:** MagicaVoxel → `npm run tree:import` → PR.
4. **Code:** animation polish, Lite mode, exporters, accessibility.

Supporting pieces:

- **Issue and PR templates**, including a tree/palette submission checklist (licence, credit name, screenshot).
- **A CI preview:** Playwright posts screenshots of the new tree or palette, in tree state and QR state, to the PR as an artifact, so reviewers see it without cloning.
- **Credit on the site:** every tree and palette card shows its author.
- `CODE_OF_CONDUCT.md`, labels (`good first issue`, `palette`, `tree`, `help wanted`).
- **Keep maintainer load small:** CI does the correctness checks; reviews focus on taste.

v1's procedural tree tools (Modular Tree, Easy Tree, tree-gen) are only needed for Option B. Their GPL and generated-output terms still need checking if used.

---

## 9. Share and export

| Export | Notes |
|---|---|
| PNG / SVG | Flat, conventional QR from the encoder output; always available |
| **Reveal video** (v1.0) | 1080 × 1080 and 1080 × 1920 (Reels/TikTok). **Render at a fixed timestep while recording**, so no frames drop. Hold the final QR for ≥ 2 s so it's scannable from the video. Use WebCodecs plus an MP4 muxer where supported, with `MediaRecorder` on `canvas.captureStream()` as fallback; check current browser support for MP4 output, since some social platforms reject WebM |
| Share link | Season, palette and seed in the URL **fragment** (`#…`), which never reaches the hosting server. Include the payload only if the user opts in |
| *(Stretch)* 3D-printable QR | Export a two-part model (base plate plus raised dark modules) for two-colour FDM printing, e.g. a 3MF that Bambu Studio maps to two filaments. Validate the minimum printed size by test prints |

---

## 10. Technology stack

| Layer | Recommendation | Note |
|---|---|---|
| Build | **Vite + React + TypeScript** | Static output; simplest for contributors. Next.js static export also works if preferred |
| 3D | Three.js + React Three Fiber + Drei | |
| Animation | GSAP (timeline, camera) + custom instanced shader | §4.1 |
| QR | `qrcode` (node-qrcode) | Pure module, no Three.js imports |
| Tests | Vitest (QR engine, mapping) + Playwright (render + decode) | ZXing JS + jsQR as decoders |
| Assets | MagicaVoxel / Blender → slot files; glTF Transform for meshes | |
| Video | WebCodecs + MP4 muxer; MediaRecorder fallback | |
| Hosting | GitHub Pages, Cloudflare Pages or Vercel (static) | |

---

## 11. Website (v1: one page)

1. **Hero = the playground:** a live tree, input box, season picker and Reveal button, all above the fold.
2. **How it works:** three steps, plus a scrubbable mini timeline showing tree ↔ QR.
3. **Seasons:** four cards; clicking one switches the hero.
4. **Open source:** repo link, licence, "add your own tree" call-out, tech stack.
5. **Footer:** credits, asset licences, trademark notice.

Docs live in the repo (`README.md`, `docs/`). Add `/gallery` and separate routes only after v1.0.

---

## 12. Performance modes

Keep v1's Full / Lite / 2D modes and practices: lazy-load the 3D bundle, instance everything, adaptive DPR, pause rendering when the tab is hidden, dispose resources on unload, a manual quality selector, and `prefers-reduced-motion`. Additions:

- The GPU morph keeps per-frame CPU work flat regardless of tile count.
- Bloom, if used at all, only in the tree state; never in the final state.
- Measure on a laptop with integrated graphics, not only a gaming GPU.

---

## 13. Repository structure

```text
seasonal-qr/
├── src/
│   ├── qr/                 # pure: encode, matrix, capacity, export (PNG/SVG)
│   ├── mapping/            # pure: slot cloud → cell pairs, delays, colours
│   ├── scene/              # R3F: tiles (instanced shader), platform, particles, camera
│   ├── timeline/           # GSAP timeline, reduced-motion variant
│   ├── seasons/            # theme + palette configs, seeds
│   ├── export/             # video recorder, share links, (stretch) 3MF
│   └── ui/                 # playground controls, density meter
├── public/
│   ├── trees/              # slot-cloud files per tree
│   └── models/             # platform/props GLB
├── tools/
│   └── tree-import/        # .vox / Blender → slot-cloud converter
├── tests/
│   ├── unit/               # Vitest: encoder, mapping determinism
│   └── scan/               # Playwright: render → screenshot → decode matrix
├── assets-manifest.json    # provenance + licence for every asset (CI-checked)
├── docs/ (architecture, animation, asset pipeline, contributing)
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

`qr/` and `mapping/` have no rendering dependencies, so they're unit-testable and reusable.

---

## 14. Licensing

- **Code:** MIT unless you deliberately want copyleft. Decide before accepting contributions.
- **Assets:** keep v1's per-asset record (source, creator, licence, attribution, modification, redistribution, commercial use) in `assets-manifest.json`. **A CI check fails if any file in `public/trees` or `public/models` lacks a manifest entry.**
- **Contributed assets:** require CC BY 4.0 or CC0 for contributed trees and palettes, stated in the PR template and recorded in the manifest, so they can be redistributed and credited.
- **Trademark:** add "QR Code is a registered trademark of DENSO WAVE INCORPORATED" to the footer and README.

---

## 15. Roadmap

| Phase | Scope | Deliverable / exit check |
|---|---|---|
| **1 — QR core** | Encoder module, flat instanced grid, scan-ready spec (§5), Playwright decode test in CI | CI decodes the final state for the full payload matrix |
| **2 — Morph with a placeholder tree** | Code-generated cone/sphere tree as a slot cloud; radial unfold; finder-first; GPU morph; scrubbing; reverse; reduced motion | Placeholder tree → QR → tree, scannable in CI at every version up to the cap |
| **3 — Sakura MVP** | First real tree (Option A or B), platform, petals, camera choreography, PNG/SVG export, density meter | **MVP release** |
| **4 — Seasons + sharing** | Three more trees, palettes, seeds, palette CI matrix, **video export**, share links | **v1.0** |
| **5 — Site, community, launch** | One-page site, docs, tree-import tool, contribution ladder (§8.1), good-first-issues, case study, demo video, launch posts (e.g. Three.js forum showcase, r/threejs, Show HN) | Public launch; case study published |
| **Later** | Lite mode for mobile, Option B art pack, 3D-printable export, `/gallery` | — |

---

## 16. MVP scope

| Feature | Priority |
|---|---|
| URL/text input with density meter and payload cap | Must |
| Genuine QR encoding (`qrcode`) | Must |
| Tile system: budget, slot cloud, radial unfold, finder-first | Must |
| GPU morph with scrub, reverse and reduced motion | Must |
| Scan-ready spec (§5) + CI decode matrix | Must |
| One Sakura tree + platform + petals | Must |
| PNG/SVG export | Must |
| Video export | v1.0 (first item after MVP) |
| Four seasons, palettes, seeds | v1.0 |
| Share links (fragment-only) | v1.0 |
| One-page site + contribution ladder + case study | v1.0 |
| Lite mobile mode, Option B art pack, printable export | Later |
| Accounts / backend | Not needed |

---

## 17. Definition of done (v1.0)

- [ ] User enters a URL or text, sees the density meter, and generates a QR.
- [ ] QR data comes from a standard encoder; the 3D grid matches its matrix exactly, including quiet zone and finder patterns.
- [ ] The final state meets every item in §5.
- [ ] CI decodes the final state for every payload × palette × version case, including degraded copies, with two decoders.
- [ ] Exported PNG, SVG and the video's final frame decode correctly.
- [ ] Tree → QR and QR → tree work, are scrubbable, and are deterministic for a given seed.
- [ ] Four seasonal trees ship, or the release states which are still planned.
- [ ] Reduced-motion and non-WebGL fallbacks work.
- [ ] Every asset has a manifest entry; licences, credits and the trademark notice are published.
- [ ] README, setup, contribution guide (including the tree-import path) and licence are published.
- [ ] Case study, demo video and README GIF are published; at least five good-first-issues are open at launch.

---

## 18. Risks

| Risk | Mitigation |
|---|---|
| QR looks right but won't scan | §5 spec + CI decode matrix with degradation + real-phone checks |
| Tile counts vary by payload and break the composition | Tile budget, payload cap, slot cloud with seeded prefix, tile scaling |
| Motion looks chaotic | Radial unfold + finder-first + radius-based timing |
| Tile tree looks like a Minecraft clone | Rounded tiles, soft lighting, a strong palette and particle work in the tree state; a decision checkpoint after the Sakura MVP |
| Performance on integrated GPUs | GPU morph, no bloom in the final state, Lite mode |
| Video export drops frames or blurs the QR | Fixed-timestep recording, final-frame hold, decode test on the final frame |
| Contributions too hard | Voxel trees + import tool + CI checks |
| Asset licences unclear | Manifest with a CI check |
| Sensitive content in share links | Fragment-only links; payload opt-in |

---

## 19. Adversarial review panel (v1 → v2)

Personas were run sequentially with a hard reset between each.

### Product Skeptic

1. The thing users take away in v1 is a PNG that looks like every other QR code. The animation is the product, and v1 gives no way to keep or share it.
2. v1 builds five routes and a docs site before proving the one moment that matters.
3. No audience or success measure is defined, so scope choices (contribution pipeline, docs depth) have no basis.

**Verdict: APPROVE WITH FIXES.** Add video export, make the landing page the playground, set the goal (§0).

### QR Correctness Pedant

1. R3F's default tone mapping changes the final colours and lowers contrast. v1 never turns it off.
2. Gaps between cubes, perspective and anti-aliasing at fractional module sizes blur or split modules. The final state needs zero gaps, orthographic projection and whole-pixel modules.
3. A quiet zone that relies on the page background fails in dark mode.
4. v1 assumes a fixed tile pool, but the tile count ranges from about 1,100 to 4,200+ depending on payload length.
5. Seasonal palettes (e.g. crimson on amber) can fail contrast. Each needs automated decode tests, including camera-like degradation.

**Verdict: APPROVE WITH FIXES.** All adopted in §3 and §5–6.

### Performance Grinch

1. Updating thousands of instance matrices on the CPU every frame is fine at 1,000 tiles, tight at 4,000+ with particles on integrated GPUs. Move interpolation into the shader.
2. Bloom, shadows and transparent foliage are the real costs; keep them out of the final state and make them optional.
3. Recording video while rendering in real time drops frames. Record at a fixed timestep.

**Verdict: APPROVE WITH FIXES.**

### Contributor / Maintainer

1. In v1, adding a tree means Blender, GLB optimisation and GPL add-on licence questions. That's a high barrier for a project that invites community trees.
2. The asset-licence manifest is good, but only if CI enforces it.
3. Next.js adds server concepts to an app with no server; Vite is simpler to clone and run.

**Verdict: APPROVE WITH FIXES.**

### Synthesis

- **Must fix before MVP:** the scan-ready spec, the CI decode matrix, the tile budget, the radial unfold, the GPU morph.
- **Can wait:** Option B art pack, Lite mode, printable export, `/gallery`.
- **Disagreement:** the Product Skeptic wants video export in the MVP; the Performance Grinch wants the MVP lean. Bet: **MVP without video, but built on the GPU morph**, which makes video export straightforward. Video is the first item after MVP.

---

## 20. References

### Core 3D and React Three Fiber

- Three.js: https://github.com/mrdoob/three.js · docs https://threejs.org/docs/ · examples https://threejs.org/examples/
- React Three Fiber: https://github.com/pmndrs/react-three-fiber · docs https://r3f.docs.pmnd.rs/
- Drei: https://github.com/pmndrs/drei · docs https://drei.docs.pmnd.rs/
- React Three Examples: https://github.com/pmndrs/react-three-examples
- Three.js `.vox` loader example: https://threejs.org/examples/#webgl_loader_vox

### Animation and effects

- GSAP: https://github.com/greensock/GSAP · docs https://gsap.com/docs/v3/
- React Three Postprocessing: https://github.com/pmndrs/react-postprocessing
- R3F animation notes: https://github.com/EnzeD/r3f-skills/tree/main/skills/r3f-animation
- Grass shader (instancing/wind reference): https://github.com/Nitash-Biswas/grass-shader-glsl

### Trees and assets

- MagicaVoxel: https://ephtracy.github.io/
- Blender: https://www.blender.org/ · manual https://docs.blender.org/manual/en/latest/
- Modular Tree: https://extensions.blender.org/add-ons/modular-tree/
- Easy Tree (GPL-3.0): https://github.com/jacobcjohnston/Easy-Tree
- tree-gen (GPL-3.0; separate terms for generated models): https://github.com/friggog/tree-gen
- glTF Transform: https://github.com/donmccurdy/glTF-Transform · docs https://gltf-transform.dev/

### QR encoding, decoding and testing

- node-qrcode: https://github.com/soldair/node-qrcode
- ZXing JS: https://github.com/zxing-js/library
- jsQR: https://github.com/cozmo/jsQR
- Playwright: https://playwright.dev/
- html5-qrcode (maintenance mode; reference only): https://github.com/mebjas/html5-qrcode

---

## 21. First implementation task

1. Encode a short test URL with `qrcode` and render the matrix as a flat instanced grid, following every §5 rule.
2. Add the Playwright test: `?t=end` → screenshot → decode with ZXing and jsQR → assert the payload. Include the degraded copy.
3. Generate a placeholder cone-shaped slot cloud in code, implement the radial unfold and GPU morph, and make CI pass at QR versions 2, 5 and 10.
4. Only then start on the Sakura tree.

This proves the hardest risk, that a beautiful 3D transformation still ends in a reliably scannable QR, before any art time is spent.
