import { useProgress } from '@react-three/drei'
import { gsap } from 'gsap'
import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import { cloudSlots, qrCells, radialUnfold } from './mapping'
import { encodeQr, gridSize, type QrResult } from './qr'
import { QrScene } from './scene/QrScene'
import { seasonFor, seasons, type Season, type SeasonEntry } from './seasons'
import { deriveSeason } from './seasons/derive'
import manifest from '../assets-manifest.json'
import { Controls, qrPng, qrSvg } from './ui/Controls'
import { ScenePicker } from './ui/ScenePicker'
import { groupOf } from './ui/scenes'
import { Story } from './ui/Story'

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
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches
const DURATION = REDUCED ? 0.3 : 5
// First visit plays the reveal once by itself; not for reduced motion, the scan-ready mode or automated browsers (tests).
let attract = !REDUCED && !END && !navigator.webdriver

const progress = { value: 0 } // the tiles' uProgress uniform
const rig = { value: 0 } // camera blend: 0 = tree view, 1 = top-down
// One timeline owns uProgress and the camera, so play / reverse / scrub stay in sync.
const tl = gsap
  .timeline({ paused: true })
  .fromTo(progress, { value: 0 }, { value: 1, duration: DURATION, ease: 'none' }, 0)
  // Plan §4: hold the tree view through settle, stamp and unfold; rise to top-down during align (72–92%).
  .fromTo(rig, { value: 0 }, { value: 1, duration: DURATION * 0.2, ease: 'power3.inOut' }, DURATION * 0.72)
if (END) tl.progress(1)

/** CSS px of the stage square; the breakpoints match the hero grid in index.html. */
function stageRoom() {
  const { innerWidth: w, innerHeight: h } = window
  if (END) return Math.min(640, w - 32) // the scan tests' framing
  if (w >= 1200) return Math.max(380, Math.min(720, h - 290, w - 760))
  if (w >= 900) return Math.max(380, Math.min(620, h - 290, w - 420))
  return Math.min(640, w - 32)
}

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

/** Plays the reveal once, holds the code, grows back; any key, tap or input from the visitor cancels what has not started. */
function playAttract() {
  const timers: number[] = []
  const later = (fn: () => void, ms: number) => timers.push(window.setTimeout(fn, ms))
  const events = ['pointerdown', 'keydown', 'input'] as const
  const cancel = () => {
    timers.forEach(clearTimeout)
    events.forEach((e) => removeEventListener(e, stop, true))
  }
  const stop = () => {
    attract = false
    cancel()
  }
  events.forEach((e) => addEventListener(e, stop, true))
  // Wait until drei's loader has parsed the model and the tab is in view, then give the visitor a beat to see it.
  const ready = () => (useProgress.getState().active || document.hidden ? later(ready, 250) : later(play, 1600))
  const play = () => {
    attract = false
    tl.play()
    later(() => {
      tl.reverse()
      stop()
    }, (DURATION + 2.5) * 1000)
  }
  later(ready, 300)
  return cancel
}

export default function App() {
  const [text, setText] = useState(INITIAL_TEXT)
  const [qr, setQr] = useState(() => (typeof initial === 'string' ? (encode(DEFAULT_TEXT) as QrResult) : initial))
  const [error, setError] = useState(typeof initial === 'string' ? initial : null)
  const [room, setRoom] = useState(stageRoom)
  useEffect(() => {
    const onResize = () => setRoom(stageRoom())
    addEventListener('resize', onResize)
    return () => removeEventListener('resize', onResize)
  }, [])

  // Season and its cloud swap together, so the ready flag never flips on tiles that belong to another season.
  const [active, setActive] = useState<{ season: Season; cloud: Cloud } | null>(null)
  const [pending, setPending] = useState<string | null>(null)
  const [seasonError, setSeasonError] = useState<string | null>(null)
  const latest = useRef('') // a slower, earlier load must not replace the scene picked after it
  function onSeason(id: string) {
    const next = seasons[id]
    latest.current = id
    setPending(id)
    load(next).then(
      (cloud) => {
        if (latest.current !== id) return
        setActive({ season: deriveSeason(next.id, next.name, cloud, next.overrides), cloud })
        setSeasonError(null)
        setPending(null)
      },
      () => {
        if (latest.current !== id) return
        setSeasonError(`Season "${next.name}" is not available yet.`)
        setPending(null)
      },
    )
  }
  useEffect(() => onSeason(INITIAL_SEASON.id), [])
  useEffect(() => (active && attract && HAS_WEBGL ? playAttract() : undefined), [active])

  // The page takes the scene's colours: its lawn is the page (and the canvas clear colour), its deep canopy the accent.
  useEffect(() => {
    if (!active) return
    const { finalLight, finalDark, tree } = active.season
    const root = document.documentElement.style
    root.setProperty('--paper', finalLight)
    root.setProperty('--accent', finalDark[2])
    root.setProperty('--bloom', tree[2])
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', finalLight)
  }, [active])

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
  const modulePx = Math.max(1, Math.floor((room * window.devicePixelRatio) / size))

  function onText(next: string) {
    setText(next)
    const result = encode(next)
    if (typeof result === 'string') return setError(result) // keep the last valid QR
    setQr(result)
    setError(null)
  }

  const scene = active && <QrScene season={active.season} pairs={pairs} gridSize={size} modulePx={modulePx} progress={progress} rig={rig} />
  // The scan-ready frame (END) is the bare canvas for the scan tests.
  if (END) return <main className="bare">{scene}</main>

  const id = active?.season.id ?? INITIAL_SEASON.id
  const group = groupOf(id)
  const index = Object.keys(seasons).indexOf(id) + 1
  const pad = (n: number) => String(n).padStart(2, '0')

  const picker = (
    <>
      <ScenePicker active={id} pending={pending} onSeason={onSeason} />
      {seasonError && active && (
        <p role="alert" className="error">
          {seasonError}
        </p>
      )}
    </>
  )
  let stage = scene
  if (!active)
    stage = seasonError ? (
      <p role="alert" className="error">
        {seasonError}
      </p>
    ) : (
      <div className="sprout" role="status">
        <div className="tiles" aria-hidden="true">
          {Array.from({ length: 25 }, (_, i) => (
            <i key={i} style={{ '--d': `${(Math.hypot((i % 5) - 2, Math.floor(i / 5) - 2) * 0.16).toFixed(2)}s` } as CSSProperties} />
          ))}
        </div>
        <span className="label">Growing the scene…</span>
      </div>
    )
  else if (!HAS_WEBGL) stage = <img className="fallback-code" src={qrPng(active.season, qr, pairs)} alt="QR code" />

  return (
    <>
      <a className="skip" href="#text">
        Skip to the text box
      </a>
      <header className="top">
        <a className="brand" href="#top" aria-label="Seasonal QR, top of the page">
          <span className="seal" lang="ja" aria-hidden="true">
            {group.kanji}
          </span>
          Seasonal QR
        </a>
        <nav aria-label="Sections">
          <a href="#how">How it works</a>
          <a href="#scenes">Scenes</a>
          <a href="#source">Open source</a>
          <a className="gh" href={REPO} aria-label="Source on GitHub">
            <svg viewBox="0 0 16 16" aria-hidden="true" fill="currentColor">
              <path d="M8 0a8 8 0 0 0-2.53 15.59c.4.07.55-.17.55-.38v-1.34c-2.23.48-2.7-1.07-2.7-1.07-.36-.92-.89-1.17-.89-1.17-.73-.5.06-.49.06-.49.8.06 1.23.83 1.23.83.72 1.22 1.88.87 2.34.66.07-.52.28-.87.5-1.07-1.78-.2-3.65-.89-3.65-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.6 7.6 0 0 1 4 0c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.28.82 2.15 0 3.07-1.87 3.75-3.66 3.95.29.25.54.73.54 1.48v2.2c0 .21.15.46.55.38A8 8 0 0 0 8 0Z" />
            </svg>
            <span>GitHub</span>
          </a>
        </nav>
      </header>
      <main id="top">
        <section className="hero" aria-labelledby="title" style={{ '--room': `${room}px` } as CSSProperties}>
          <div className="title">
            <p className="eyebrow label">
              <span>
                Scene {pad(index)} / {pad(Object.keys(seasons).length)}
              </span>
              <b>{seasons[id].name}</b>
            </p>
            <h1 id="title">A garden that falls into a QR code.</h1>
          </div>
          <div className="lede">
            <p>Type a link, pick a scene, press Reveal. The diorama sheds from the top down and every tile lands as one module of a real, scannable code. It all runs in your browser; nothing is uploaded.</p>
            <dl className="facts">
              <dt>Codes</dt>
              <dd>Real QR, up to version 10</dd>
              <dt>Exports</dt>
              <dd>PNG, SVG, 1080 px video</dd>
              <dt>Licence</dt>
              <dd>MIT code, CC0 models</dd>
            </dl>
          </div>
          <div className="stage">{stage}</div>
          {!active && <div className="side">{picker}</div>}
          {active &&
            (HAS_WEBGL ? (
              <Controls season={active.season} picker={picker} tl={tl} text={text} error={error} qr={qr} onText={onText} pairs={pairs} seed={SEED} />
            ) : (
              <>
                <div className="side">{picker}</div>
                <div className="dock">
                  <p>The 3D reveal needs WebGL, which is unavailable here. Here is the flat QR code.</p>
                  <label className="label" htmlFor="text">
                    Link or text
                  </label>
                  <input id="text" value={text} onChange={(e) => onText(e.target.value)} aria-invalid={!!error} />
                  <p role="alert" className="error">
                    {error}
                  </p>
                  <div className="actions">
                    <a href={`data:image/svg+xml,${encodeURIComponent(qrSvg(active.season, qr, pairs))}`} download="seasonal-qr.svg">
                      Download SVG
                    </a>
                    <a href={qrPng(active.season, qr, pairs)} download="seasonal-qr.png">
                      Download PNG
                    </a>
                  </div>
                </div>
              </>
            ))}
        </section>
        <Story active={id} onSeason={onSeason} />
      </main>
      <footer>
        <p className="sign">
          Seasonal QR
          <span>
            Made in the open · <a href={REPO}>github.com/gabriel0139/seasonal-qr</a>
          </span>
        </p>
        <p>
          Scene models:{' '}
          {/* one line while every scene shares an author and licence; per scene once a contribution differs */}
          {new Set(CREDITS.map((c) => c.author + c.licence)).size === 1
            ? `${CREDITS[0].author} · ${CREDITS[0].licence}`
            : CREDITS.map((c) => `${c.name[0].toUpperCase()}${c.name.slice(1)} · ${c.author} · ${c.licence}`).join('; ')}
          .
        </p>
        <p>Code: MIT licence. Fonts: Shippori Mincho, Instrument Sans and IBM Plex Mono, SIL Open Font Licence.</p>
        <p>QR Code is a registered trademark of DENSO WAVE INCORPORATED.</p>
      </footer>
    </>
  )
}
