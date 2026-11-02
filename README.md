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

### Adding a season

Add an entry (`id`, `name`) to `src/seasons/index.ts` and drop in `public/models/<id>.glb` and `public/trees/<id>.json`. The GLB needs the nodes `Trunk`, `Blossoms`, `Base`, `Props`, `Water`. CI decodes every season whose GLB exists, with every payload, so no test changes are needed.

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

- `?text=<url-encoded payload>` — content to encode (capped at QR version 10, EC level M). A density meter under the input shows the size class, byte count and QR version; the "Download PNG" and "Download SVG" links save the current code.
- `&season=<id>` — which tree to grow (`sakura`, `summer`, `autumn`, `winter`). Without it, or with an unknown id, the site picks the season from today's date (northern hemisphere: sakura from 20 March, summer from 21 June, autumn from 22 September, winter from 21 December). The Season picker switches it live.
- `&t=end` — jump straight to the scan-ready final frame; used by the Playwright scan tests, which wait for `body[data-ready="true"]`.
- `&seed=<int>` — deterministic seed for the tree layout and unfold jitter.
- The same keys also work in the URL fragment (`#text=…&season=…&seed=…`), which takes precedence over the query. "Copy link" produces fragment links, so the payload never reaches a server.
