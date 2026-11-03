# seasonal-qr
A seasonal 3D tree that unfolds into a real, scannable QR code. Built with Three.js and React Three Fiber; runs entirely in your browser.

Each season is a Blender-built model (`public/models/<id>.glb`) with its QR tiles hidden inside. Four ship: sakura, summer, autumn, winter. `npm run tree:build` rebuilds them all, and Blender is needed only for that.

## Development

```sh
npm ci                 # install dependencies
npm run dev            # start the dev server
npm test               # unit tests (vitest)
npm run test:scan      # scan tests: render, then decode with two independent decoders
npm run reveal:strip   # renders the reveal as a frame strip for review
```

The scan test renders each payload in headless Chromium, then checks that both jsQR and ZXing decode the exact text, both from the canvas and from a degraded (downscaled, blurred, JPEG) copy that mimics a phone camera.

"Export video" renders the reveal at a fixed 30 fps to a 1080 × 1080 file (H.264 MP4 where the browser can encode it, otherwise VP9 WebM) that holds the scan-ready code for 2 s; it needs WebCodecs (Chrome, Edge or Safari 17+), with no MediaRecorder fallback yet, and a scan test decodes the video's last frame.

QR Code is a registered trademark of DENSO WAVE INCORPORATED.

### Contributing

See `CONTRIBUTING.md` for the contribution ladder (QR colour overrides, then trees, then code), licence rules and the PR checklist. CI checks every asset against `assets-manifest.json`, decodes every season, and attaches tree and QR screenshots of each season to the Playwright report so reviewers can see a new tree without cloning.

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

The built-in seasons come from `tools/tree-build/<id>.py` (`npm run tree:build` writes both files). `.blend` files are not committed: the scripts are the source. `npm run tree:open -- <season>` opens the built scene in Blender for visual tweaking, without sampling slots or overwriting the committed assets; carry your changes back into the script.

### URL parameters

- `?text=<url-encoded payload>` — content to encode (capped at QR version 10, EC level M). A QR code holds a few hundred bytes, so to share a document or folder, host it elsewhere (Google Drive, Dropbox, a GitHub release) and encode its share link; nothing is ever uploaded through this site. A density meter under the input shows the size class, byte count and QR version; the "Download PNG" and "Download SVG" links save the current code.
- `&season=<id>` — which tree to grow (`sakura`, `summer`, `autumn`, `winter`). Without it, or with an unknown id, the site picks the season from today's date (northern hemisphere: sakura from 20 March, summer from 21 June, autumn from 22 September, winter from 21 December). The Season picker switches it live.
- `&t=end` — jump straight to the scan-ready final frame; used by the Playwright scan tests, which wait for `body[data-ready="true"]`.
- `&seed=<int>` — deterministic seed for the tree layout and unfold jitter.
- The same keys also work in the URL fragment (`#text=…&season=…&seed=…`), which takes precedence over the query. "Copy link" produces fragment links, so the payload never reaches a server.
