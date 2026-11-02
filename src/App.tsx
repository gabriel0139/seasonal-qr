import { gsap } from 'gsap'
import { useMemo, useState } from 'react'
import sakura from '../public/trees/sakura.json'
import { cloudSlots, qrCells, radialUnfold } from './mapping'
import { encodeQr, gridSize, type QrResult } from './qr'
import { QrScene } from './scene/QrScene'
import { Controls } from './ui/Controls'

// URL contract: docs-contract.md
const DEFAULT_TEXT = 'https://google.com'
const params = new URLSearchParams(location.search)
const INITIAL_TEXT = params.get('text') ?? DEFAULT_TEXT
const END = params.get('t') === 'end'
const parsedSeed = Number.parseInt(params.get('seed') ?? '', 10)
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

export default function App() {
  const [text, setText] = useState(INITIAL_TEXT)
  const [qr, setQr] = useState(() => (typeof initial === 'string' ? (encode(DEFAULT_TEXT) as QrResult) : initial))
  const [error, setError] = useState(typeof initial === 'string' ? initial : null)

  const size = gridSize(qr.version)
  // Mosaic: dark modules take non-lawn tiles (tree, props), light modules and the quiet zone take lawn (palette index 4).
  const pairs = useMemo(() => {
    const cells = qrCells(qr)
    const dark = cells.filter((c) => c.dark)
    const light = cells.filter((c) => !c.dark)
    return [
      ...radialUnfold(cloudSlots(sakura, dark.length, (p) => p !== 4), dark, size, SEED),
      ...radialUnfold(cloudSlots(sakura, light.length, (p) => p === 4), light, size, SEED),
    ]
  }, [qr, size])
  const modulePx = Math.max(1, Math.floor((Math.min(640, window.innerWidth - 32) * window.devicePixelRatio) / size))

  function onText(next: string) {
    setText(next)
    const result = encode(next)
    if (typeof result === 'string') return setError(result) // keep the last valid QR
    setQr(result)
    setError(null)
  }

  return (
    <main>
      <QrScene pairs={pairs} gridSize={size} modulePx={modulePx} progress={progress} rig={rig} />
      {!END && <Controls tl={tl} text={text} error={error} qr={qr} onText={onText} pairs={pairs} />}
    </main>
  )
}
