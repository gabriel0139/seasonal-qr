# seasonal-qr
A seasonal 3D tree that unfolds into a real, scannable QR code. Built with Three.js and React Three Fiber; runs entirely in your browser.

The tree is a Blender-built model (`public/models/sakura.glb`) with its QR tiles hidden inside; `npm run tree:build` rebuilds it, and Blender is needed only for that.

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

Add an entry to `src/seasons/index.ts` (palette: start colours, deep landed colours, pale light colour) and drop in `public/models/<id>.glb` and `public/trees/<id>.json`. The GLB needs the nodes `Trunk`, `Blossoms`, `Base`, `Props`, `Water`; slot classes are 0 trunk, 1–3 canopy shades, 4 lawn, 5 wood, 6 stone, 7 water. CI decodes every season whose GLB exists, with every payload, so no test changes are needed.

### URL parameters

- `?text=<url-encoded payload>` — content to encode (capped at QR version 10, EC level M). A density meter under the input shows the size class, byte count and QR version; the "Download PNG" and "Download SVG" links save the current code.
- `&season=<id>` — which tree to grow (`sakura`, `autumn`); unknown ids fall back to `sakura`. The Season picker switches it live.
- `&t=end` — jump straight to the scan-ready final frame; used by the Playwright scan tests, which wait for `body[data-ready="true"]`.
- `&seed=<int>` — deterministic seed for the tree layout and unfold jitter.
- The same keys also work in the URL fragment (`#text=…&season=…&seed=…`), which takes precedence over the query. "Copy link" produces fragment links, so the payload never reaches a server.
