# Seasonal QR

[![CI](https://github.com/gabriel0139/seasonal-qr/actions/workflows/ci.yml/badge.svg)](https://github.com/gabriel0139/seasonal-qr/actions/workflows/ci.yml)
[![Licence: MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)

A seasonal 3D tree that unfolds into a real, scannable QR code.

Type a URL or some text, pick a season, press **Reveal the code**: the tiles hidden inside the tree fly out and settle into a QR code on the lawn, in the colours of the scene. Scan it from the screen, download it as PNG or SVG, or export the whole reveal as a video. Everything runs in your browser; nothing is uploaded.

<!-- Demo GIF goes here once the site is deployed (Phase 5b). -->

## Features

- **Genuine QR codes.** Encoded with [node-qrcode](https://github.com/soldair/node-qrcode), up to version 10 at error-correction level M. A density meter shows the size as you type.
- **Four seasons.** Sakura, summer, autumn and winter dioramas, picked by today's date or by hand.
- **A mosaic, not black on white.** Dark modules land in deep versions of the scene's own colours; light modules and the quiet zone use the lawn.
- **Scrubbable, reversible reveal.** One timeline drives the tiles and the camera on the GPU; drag the progress slider or press **Grow back**.
- **Exports.** PNG, SVG, a 1080 × 1080 reveal video that ends on the scannable code, and share links that keep the payload in the URL fragment.
- **Scan correctness enforced by CI.** Every season × payload is rendered in headless Chromium and decoded by two independent decoders, direct and camera-degraded.

## Quick start

Requires Node.js 22 or newer.

```sh
git clone https://github.com/gabriel0139/seasonal-qr.git
cd seasonal-qr
npm ci
npm run dev        # http://localhost:5173
```

`npm run build` writes a static site to `dist/`; host it anywhere that serves static files.

## Usage

Type or paste into the **Text** box, choose a **Season**, press **Reveal the code**. The buttons below the scene download the flat PNG or SVG, copy a share link, or export the reveal as a video.

A QR code holds a few hundred bytes, so a document or folder cannot fit inside one. To share a file, host it elsewhere (Google Drive, Dropbox, a GitHub release) and encode its share link.

**Export video** renders the reveal at a fixed 30 fps to a 1080 × 1080 file (H.264 MP4 where the browser can encode it, otherwise VP9 WebM) that holds the scan-ready code for 2 s. It needs WebCodecs (Chrome, Edge or Safari 17+); there is no MediaRecorder fallback yet.

Without WebGL the page shows the flat code with the download links instead of the 3D scene.

### URL parameters

- `?text=<url-encoded payload>` — content to encode (capped at QR version 10, EC level M). A density meter under the input shows the size class, byte count and QR version.
- `&season=<id>` — which tree to grow (`sakura`, `summer`, `autumn`, `winter`). Without it, or with an unknown id, the site picks the season from today's date (northern hemisphere: sakura from 20 March, summer from 21 June, autumn from 22 September, winter from 21 December). The Season picker switches it live.
- `&t=end` — jump straight to the scan-ready final frame; used by the Playwright scan tests, which wait for `body[data-ready="true"]`.
- `&seed=<int>` — deterministic seed for the tree layout and unfold jitter.
- The same keys also work in the URL fragment (`#text=…&season=…&seed=…`), which takes precedence over the query. **Copy link** produces fragment links, so the payload never reaches a server.

## How it works

- **Every QR cell is a tile.** The final code is `(n + 8)²` tiles, `n = 4 × version + 17`, including a four-module quiet zone rendered as light tiles so the code still scans on a dark page. That is 1,089 tiles at version 2 and 4,225 at version 10.
- **The tiles start inside the tree.** Each season is a Blender-built model (`public/models/<id>.glb`) plus a slot cloud (`public/trees/<id>.json`) of points sampled inside its trunk, canopy, lawn and props. Dark modules take tree and prop slots; light modules take lawn slots.
- **Radial unfold.** Tree height maps to grid radius and azimuth to grid angle, finder patterns land first, so the motion reads as intentional and the code becomes recognisable early.
- **GPU morph.** Start and end positions, colours and delays live in instanced attributes; one progress uniform drives them, so scrubbing, reversing and fixed-timestep video export come for free.
- **Scan-ready final frame.** Orthographic top-down camera, whole device pixels per module, tone mapping off, unlit colours, zero gaps, no post-processing or particles, dark on light. These are the renderer settings that silently break scanning when missed.

The full design is in [`seasonal-qr-project-plan.md`](seasonal-qr-project-plan.md) and the decisions behind it in [`running_decisions.md`](running_decisions.md).

## Contributing

Contributions are welcome, from a colour tweak to a whole new tree. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the contribution ladder (QR colour overrides, then trees, then code), licence rules and the PR checklist, and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). CI checks every asset against `assets-manifest.json`, decodes every season, and attaches tree and QR screenshots of each season to the Playwright report, so reviewers can see a new tree without cloning.

### Adding a season

Add an entry (`id`, `name`) to `src/seasons/index.ts` and drop in `public/models/<id>.glb` and `public/trees/<id>.json`. CI decodes every season whose GLB exists, with every payload, so no test changes are needed.

No Blender needed: `npm run tree:import -- <id> path/to/model.glb` copies any GLB to `public/models/<id>.glb` and samples `public/trees/<id>.json` from it with the same rules as the Blender build. The GLB must be Y up and have:

- root nodes `Trunk`, `Blossoms` and `Base`, each closed (watertight and consistently wound; up to 0.1% open edges are tolerated for decimation slits). `Blossoms` may be several overlapping closed shells.
- `Base` with its top at y = 0 and within ±36 in x and z. Its most up-facing material is the lawn colour. Faces with a material named `PondBed` mark a pond basin, which lawn slots keep 1.0 clear of.
- optionally a root `Props`, whose children are scenery that the lawn slots keep clear of. Children with these names also hold slots: `Bridge` (wood) and `Lantern` or `Rocks` (stone), which must be closed, and `Water`, an open disc at the pond surface with pond-water slots under it. A class whose prop is missing or too thin gives its share to the canopy.

The tool stops with a message that names the node and the broken rule. Before writing anything it checks its own output: every slot re-passes its class test, the class counts and shares hold, and every prefix the QR grids use keeps the class mix. Palette: trunk is the material covering most of `Trunk`; canopy deep, mid and pale are the darkest, second-darkest and lightest `Blossoms` materials; wood, stone and water are the first material of `Bridge`, `Lantern` (or `Rocks`) and `Water`. Without them it uses the trunk colour, `#3d4049` and `#173f66`.

The JSON carries everything else about the season, `{"name", "baseSize", "palette", "slots"}`:

- `baseSize`: width of the base top in world units (the landed QR spans it).
- `slots`: `[x, y, z, p]` points inside the model (GLB space, Y up), `p` the slot class below.
- `palette`: 8 sRGB hex colours, one per class, from the material that class sits in. The app uses them as the tile start colours and, unless the season's registry entry sets `overrides` (`finalDark`, `finalLight`, `petals`), derives the landed QR colours from them (deep darks, pale light), so a new season needs no colour code. The built-in seasons set hand-tuned overrides in `src/seasons/index.ts`; CI decodes either way.

| p | class | | p | class |
|---|---|---|---|---|
| 0 | trunk | | 4 | lawn |
| 1 | canopy deep | | 5 | wood |
| 2 | canopy mid | | 6 | stone |
| 3 | canopy pale | | 7 | pond water |

The built-in seasons come from `tools/tree-build/<id>.py` (`npm run tree:build` writes both files; Blender is needed only for that). `.blend` files are not committed: the scripts are the source. `npm run tree:open -- <season>` opens the built scene in Blender for visual tweaking, without sampling slots or overwriting the committed assets; carry your changes back into the script.

## Development

```sh
npm run dev            # dev server
npm run typecheck      # tsc
npm test               # unit tests (vitest): QR engine, mapping, season colours, manifest, tree import
npm run test:scan      # scan tests (Playwright): render, then decode with two independent decoders
npm run build          # static site in dist/
npm run reveal:strip   # render the reveal as a frame strip for review
npm run tree:import -- <id> <model.glb>   # import a season from any GLB
npm run tree:build     # rebuild the built-in seasons with Blender
```

The scan tests render each payload in headless Chromium, then check that both jsQR and ZXing decode the exact text, from the canvas and from a degraded (downscaled, blurred, JPEG) copy that mimics a phone camera. They also decode the exported PNG, SVG and the last frame of the exported video. A change that breaks them does not merge.

Built with [Three.js](https://threejs.org/), [React Three Fiber](https://r3f.docs.pmnd.rs/), [GSAP](https://gsap.com/), [node-qrcode](https://github.com/soldair/node-qrcode), [mediabunny](https://github.com/Vanilagy/mediabunny), [Vite](https://vite.dev/), [Vitest](https://vitest.dev/) and [Playwright](https://playwright.dev/).

## Roadmap

- [x] QR engine, radial unfold, GPU morph, CI decode matrix
- [x] Sakura MVP with PNG and SVG export
- [x] Four seasons, video export, share links
- [x] Tree-import tool and contribution path
- [ ] Deployed site, demo video, case study
- [ ] Lite mode for mobile, 3D-printable export

## Licence

Code is [MIT](LICENSE). The tree models and slot clouds are CC0 1.0; every asset's licence and author are listed in [`assets-manifest.json`](assets-manifest.json). Contributed assets must be CC BY 4.0 or CC0.

QR Code is a registered trademark of DENSO WAVE INCORPORATED.
