# seasonal-qr
A seasonal 3D tree that unfolds into a real, scannable QR code. Built with Three.js and React Three Fiber; runs entirely in your browser.

## Development

```sh
npm ci                 # install dependencies
npm run dev            # start the dev server
npm test               # unit tests (vitest)
npm run test:scan      # scan tests: render, then decode with two independent decoders
```

The scan test renders each payload in headless Chromium, then checks that both jsQR and ZXing decode the exact text, both from the canvas and from a degraded (downscaled, blurred, JPEG) copy that mimics a phone camera.

QR Code is a registered trademark of DENSO WAVE INCORPORATED.

### URL parameters

- `?text=<url-encoded payload>` — content to encode (capped at QR version 10, EC level M).
- `&t=end` — jump straight to the scan-ready final frame; used by the Playwright scan tests, which wait for `body[data-ready="true"]`.
- `&seed=<int>` — deterministic seed for the tree layout and unfold jitter.
