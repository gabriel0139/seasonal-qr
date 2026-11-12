// Renders the site's images from the built scenes: picker/gallery thumbnails, the "how it works" frames and the OG card.
// Re-run after any model changes: node tools/thumbs.mjs   (needs Blender; the frames start the dev server like reveal:strip)
import { execFileSync } from 'node:child_process'
import { mkdtempSync, readdirSync, readFileSync, mkdirSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { chromium } from '@playwright/test'
import jsQR from 'jsqr'
import sharp from 'sharp'

const BLENDER = process.env.BLENDER ?? '/Applications/Blender.app/Contents/MacOS/Blender'
const root = new URL('..', import.meta.url).pathname
const tmp = mkdtempSync(join(tmpdir(), 'seasonal-qr-thumbs-'))
const ids = readdirSync(join(root, 'public/models')).filter((f) => f.endsWith('.glb')).map((f) => f.slice(0, -4))
const STORY = 'sakura' // the scene the "how it works" frames show
const REPO = 'https://github.com/gabriel0139/seasonal-qr'

/** A path under public/, its folder created. */
function out(...p) {
  mkdirSync(join(root, 'public', ...p.slice(0, -1)), { recursive: true })
  return join(root, 'public', ...p)
}

/** Transparent Blender render of one scene, trimmed to the model so every scene is framed the same way. */
async function render(id) {
  const png = join(tmp, `${id}.png`)
  execFileSync(BLENDER, ['-b', '-P', join(root, 'tools/tree-build/preview.py'), '--', join(root, 'public/models', `${id}.glb`), png, '--size=900', '--transparent'], { stdio: 'ignore' })
  return sharp(png).trim({ threshold: 0 }).toBuffer()
}

const renders = {}
for (const id of ids) {
  renders[id] = await render(id)
  const file = out('thumbs', `${id}.webp`)
  const { size } = await sharp(renders[id])
    .resize(400, 400, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } })
    .webp({ quality: 72, alphaQuality: 70, effort: 6 })
    .toFile(file)
  console.log(`thumbs/${id}.webp ${(size / 1024).toFixed(1)} KB`)
}

// Four frames of the real reveal, from the same capture tool reviewers use.
const strip = join(tmp, 'strip.png')
// The landed code points at the repository, so the one on the OG card scans to something useful.
execFileSync('node', [join(root, 'tools/reveal-strip.mjs'), `--season=${STORY}`, `--text=${REPO}`, '--frames=4', '--size=520', `--out=${strip}`], { stdio: 'inherit' })
const { width, height } = await sharp(strip).metadata()
const cell = (width - 3 * 8) / 4 // reveal-strip lays frames out in one row with 8 px gutters
for (let i = 0; i < 4; i++) {
  // The scene frames are cropped in on the diorama; the last keeps the whole code, quiet zone included.
  const side = Math.round(i < 3 ? cell * 0.8 : cell)
  const top = Math.min(height - side, Math.max(0, Math.round(height * 0.55 - side / 2)))
  const { size } = await sharp(strip)
    .extract({ left: Math.round(i * (cell + 8) + (cell - side) / 2), top: i < 3 ? top : 0, width: side, height: side })
    .resize(480, 480, { kernel: i < 3 ? 'lanczos3' : 'nearest' })
    .webp({ quality: 80, effort: 6 })
    .toFile(out('story', `${i + 1}.webp`))
  console.log(`story/${i + 1}.webp ${(size / 1024).toFixed(1)} KB`)
}

// OG card, 1200 × 630, built like the site: the landed code sits on its own lawn colour, so it has no edge.
const data = (buf, type) => `data:${type};base64,${buf.toString('base64')}`
const font = (f) => data(readFileSync(join(root, 'public/fonts', f)), 'font/woff2')
const code = await sharp(strip).extract({ left: Math.round(3 * (cell + 8)), top: 0, width: Math.round(cell), height }).png().toBuffer()
// The OG card and the last story frame claim a working code: check it scans before writing the card.
const { data: rgba, info } = await sharp(code).ensureAlpha().raw().toBuffer({ resolveWithObject: true })
if (jsQR(new Uint8ClampedArray(rgba), info.width, info.height)?.data !== REPO) throw new Error('the landed code in the reveal strip does not scan')
const lawn = `rgb(${[...(await sharp(code).extract({ left: 1, top: 1, width: 1, height: 1 }).removeAlpha().raw().toBuffer())]})`
const scenes = await Promise.all(['sakura', 'summer', 'autumn', 'winter'].filter((id) => renders[id]).map((id) => sharp(renders[id]).resize(420, 420, { fit: 'inside' }).png().toBuffer()))
const browser = await chromium.launch()
try {
  const page = await browser.newPage({ viewport: { width: 1200, height: 630 } })
  await page.setContent(`<!doctype html><style>
    @font-face { font-family: M; src: url(${font('shippori-mincho-500.woff2')}); }
    @font-face { font-family: S; src: url(${font('instrument-sans.woff2')}); font-weight: 400 700; }
    @font-face { font-family: P; src: url(${font('ibm-plex-mono-400.woff2')}); }
    * { margin: 0; box-sizing: border-box; }
    body { width: 1200px; height: 630px; background: ${lawn}; color: #241a14; font-family: S; position: relative; overflow: hidden; }
    .brand { position: absolute; left: 64px; top: 56px; display: flex; align-items: center; gap: 16px; font: 30px/1 M; }
    .seal { width: 46px; height: 46px; border-radius: 4px; background: #8c1f52; color: #f8eef0; font: 27px/46px M; text-align: center; }
    .kicker { margin-left: 8px; font: 14px/1 P; letter-spacing: .08em; text-transform: uppercase; color: #5b5440; }
    h1 { position: absolute; left: 64px; top: 152px; width: 660px; font: 500 62px/1.06 M; letter-spacing: -0.02em; }
    p { position: absolute; left: 64px; top: 304px; width: 560px; font: 23px/1.4 S; color: #3c3a2c; }
    .code { position: absolute; right: 40px; top: 105px; width: 420px; height: 420px; image-rendering: pixelated; }
    .row { position: absolute; left: 22px; bottom: 6px; display: flex; align-items: flex-end; }
    .row img { width: 205px; margin-right: -22px; }
  </style>
  <div class="brand"><div class="seal">春</div>Seasonal QR<span class="kicker">Open source · nothing uploaded</span></div>
  <h1>A garden that falls into a QR&nbsp;code.</h1>
  <p>Eight 3D scenes shed, tile by tile, into a real, scannable code.</p>
  <img class="code" src="${data(code, 'image/png')}">
  <div class="row">${scenes.map((b) => `<img src="${data(b, 'image/png')}">`).join('')}</div>`)
  await page.evaluate(() => document.fonts.ready)
  const { size } = await sharp(await page.screenshot()).jpeg({ quality: 86, mozjpeg: true }).toFile(out('og.jpg'))
  console.log(`og.jpg ${(size / 1024).toFixed(1)} KB`)
} finally {
  await browser.close()
  rmSync(tmp, { recursive: true, force: true })
}
