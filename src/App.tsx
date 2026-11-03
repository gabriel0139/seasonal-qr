import { gsap } from 'gsap'
import { useEffect, useMemo, useState } from 'react'
import { cloudSlots, qrCells, radialUnfold } from './mapping'
import { encodeQr, gridSize, type QrResult } from './qr'
import { QrScene } from './scene/QrScene'
import { seasonFor, seasons, type Season, type SeasonEntry } from './seasons'
import { deriveSeason } from './seasons/derive'
import manifest from '../assets-manifest.json'
import { Controls, qrPng, qrSvg } from './ui/Controls'

// URL contract: docs-contract.md
const DEFAULT_TEXT = 'https://google.com'
const params = new URLSearchParams(location.search)
const fragment = new URLSearchParams(location.hash.slice(1)) // share links: fragment wins over query
const param = (key: string) => fragment.get(key) ?? params.get(key)
const INITIAL_TEXT = param('text') ?? DEFAULT_TEXT
const INITIAL_SEASON = seasons[param('season') ?? ''] ?? seasons[seasonFor()]
const REPO = 'https://github.com/gabriel0139/seasonal-qr'
const HAS_WEBGL = (() => {
  const c = document.createElement('canvas')
  return !!(c.getContext('webgl2') ?? c.getContext('webgl'))
})()
const CREDITS = manifest.filter((m) => m.slots).map((m) => ({ ...m, name: m.path.replace(/^.*\//, '').replace(/\.\w+$/, '') }))
const END = param('t') === 'end'
const parsedSeed = Number.parseInt(param('seed') ?? '', 10)
const SEED = Number.isFinite(parsedSeed) ? parsedSeed : 1
const DURATION = matchMedia('(prefers-reduced-motion: reduce)').matches ? 0.3 : 5

const progress = { value: 0 } // the tiles' uProgress uniform
const rig = { value: 0 } // camera blend: 0 = tree view, 1 = top-down
// One timeline owns uProgress and the camera, so play / reverse / scrub stay in sync.
const tl = gsap
  .timeline({ paused: true })
  .fromTo(progress, { value: 0 }, { value: 1, duration: DURATION, ease: 'none' }, 0)
  // Plan §4: hold the tree view through settle, stamp and unfold; rise to top-down during align (72–92%).
  .fromTo(rig, { value: 0 }, { value: 1, duration: DURATION * 0.2, ease: 'power3.inOut' }, DURATION * 0.72)
if (END) tl.progress(1)

/** QrResult, or an error message to show inline. */
function encode(text: string): QrResult | string {
  if (!text) return 'Enter some text to encode.'
  try {
    return encodeQr(text)
  } catch (e) {
    if (e instanceof RangeError) return 'Too long for a version 10 QR code. Shorten the text.'
    throw e
  }
}

const initial = encode(INITIAL_TEXT)

type Cloud = { slots: number[][]; palette: string[]; baseSize: number }

/** The season's slot cloud; throws if its files are missing (the dev server answers 404s with index.html, hence the content-type check). */
async function load(season: SeasonEntry): Promise<Cloud> {
  const [cloud, glb] = await Promise.all([fetch(`/trees/${season.id}.json`), fetch(`/models/${season.id}.glb`)])
  if (!cloud.ok || !glb.ok || /html/.test(cloud.headers.get('content-type') ?? '') || /html/.test(glb.headers.get('content-type') ?? '')) {
    throw new Error(`missing files for ${season.id}`)
  }
  return cloud.json()
}

export default function App() {
  const [text, setText] = useState(INITIAL_TEXT)
  const [qr, setQr] = useState(() => (typeof initial === 'string' ? (encode(DEFAULT_TEXT) as QrResult) : initial))
  const [error, setError] = useState(typeof initial === 'string' ? initial : null)

  // Season and its cloud swap together, so the ready flag never flips on tiles that belong to another season.
  const [active, setActive] = useState<{ season: Season; cloud: Cloud } | null>(null)
  const [seasonError, setSeasonError] = useState<string | null>(null)
  function onSeason(id: string) {
    const next = seasons[id]
    load(next).then(
      (cloud) => {
        setActive({ season: deriveSeason(next.id, next.name, cloud, next.overrides), cloud })
        setSeasonError(null)
      },
      () => setSeasonError(`Season "${next.name}" is not available yet.`),
    )
  }
  useEffect(() => onSeason(INITIAL_SEASON.id), [])

  const size = gridSize(qr.version)
  // Mosaic: dark modules take non-lawn tiles (tree, props), light modules and the quiet zone take lawn (palette index 4).
  const pairs = useMemo(() => {
    if (!active) return []
    const cells = qrCells(qr)
    const dark = cells.filter((c) => c.dark)
    const light = cells.filter((c) => !c.dark)
    return [
      ...radialUnfold(cloudSlots(active.cloud, dark.length, (p) => p !== 4), dark, size, SEED),
      ...radialUnfold(cloudSlots(active.cloud, light.length, (p) => p === 4), light, size, SEED),
    ]
  }, [qr, size, active])
  const modulePx = Math.max(1, Math.floor((Math.min(640, window.innerWidth - 32) * window.devicePixelRatio) / size))

  function onText(next: string) {
    setText(next)
    const result = encode(next)
    if (typeof result === 'string') return setError(result) // keep the last valid QR
    setQr(result)
    setError(null)
  }

  if (!active) return seasonError ? <p role="alert" className="error">{seasonError}</p> : null
  return (
    <>
      {!END && (
        <header>
          <h1>Seasonal QR</h1>
          <p>
            A seasonal tree that unfolds into a real, scannable QR code. Runs in your browser, nothing is uploaded.{' '}
            <a href={REPO}>GitHub</a>
          </p>
        </header>
      )}
      <main>
        {HAS_WEBGL ? (
          <QrScene season={active.season} pairs={pairs} gridSize={size} modulePx={modulePx} progress={progress} rig={rig} />
        ) : (
          <div className="controls">
            <p>The 3D reveal needs WebGL, which is unavailable here. Here is the flat QR code.</p>
            <img src={qrPng(active.season, qr, pairs)} alt="QR code" style={{ width: '100%', maxWidth: 320, imageRendering: 'pixelated' }} />
            <label>
              Text
              <input value={text} onChange={(e) => onText(e.target.value)} aria-invalid={!!error} />
            </label>
            <p role="alert" className="error">{error}</p>
            <div className="row">
              <a href={`data:image/svg+xml,${encodeURIComponent(qrSvg(active.season, qr, pairs))}`} download="seasonal-qr.svg">Download SVG</a>
              <a href={qrPng(active.season, qr, pairs)} download="seasonal-qr.png">Download PNG</a>
            </div>
          </div>
        )}
        {HAS_WEBGL && !END && <Controls season={active.season} seasonError={seasonError} onSeason={onSeason} tl={tl} text={text} error={error} qr={qr} onText={onText} pairs={pairs} seed={SEED} />}
      </main>
      {!END && (
        <footer>
          <p>
            Tree models:{' '}
            {CREDITS.map((c) => `${c.name[0].toUpperCase()}${c.name.slice(1)} · ${c.author} · ${c.licence}`).join('; ')}.
          </p>
          <p>Code: MIT licence.</p>
          <p>QR Code is a registered trademark of DENSO WAVE INCORPORATED.</p>
        </footer>
      )}
    </>
  )
}
