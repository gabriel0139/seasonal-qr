import { useEffect, useMemo, useState } from 'react'
import type { TilePair } from '../mapping'
import { density, MAX_VERSION, QUIET_ZONE, type QrResult } from '../qr'
import { sakura } from '../seasons/sakura'

interface Props {
  tl: gsap.core.Timeline
  text: string
  error: string | null
  qr: QrResult
  pairs: TilePair[]
  onText: (text: string) => void
}

/** Dark modules grouped by mosaic colour, as [col, row] in grid coordinates (quiet zone included). */
function darkByColour(pairs: TilePair[]): Map<string, number[][]> {
  const by = new Map<string, number[][]>()
  for (const { cell, slot } of pairs) {
    if (!cell.dark) continue
    const colour = sakura.finalDark[slot.paletteIndex]
    by.set(colour, [...(by.get(colour) ?? []), [cell.col, cell.row]])
  }
  return by
}

/** Flat SVG of the same mosaic the tiles show (plan §5.9 fallback). */
function qrSvg({ size }: QrResult, pairs: TilePair[]): string {
  const g = size + 2 * QUIET_ZONE
  const paths = [...darkByColour(pairs)]
    .map(([colour, cs]) => `<path d="${cs.map(([c, r]) => `M${c} ${r}h1v1h-1z`).join('')}" fill="${colour}"/>`)
    .join('')
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${g} ${g}" shape-rendering="crispEdges"><rect width="${g}" height="${g}" fill="${sakura.finalLight}"/>${paths}</svg>`
}

/** Flat PNG at 10 px per module, same mosaic as qrSvg. */
function qrPng({ size }: QrResult, pairs: TilePair[]): string {
  const px = 10
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = (size + 2 * QUIET_ZONE) * px
  const ctx = canvas.getContext('2d')
  if (!ctx) return '' // no canvas support (e.g. jsdom without the canvas package)
  ctx.fillStyle = sakura.finalLight
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  for (const [colour, cs] of darkByColour(pairs)) {
    ctx.fillStyle = colour
    for (const [c, r] of cs) ctx.fillRect(c * px, r * px, px, px)
  }
  return canvas.toDataURL('image/png')
}

const LABELS = ['Short', 'Medium', 'Dense'] as const
/** Byte-mode capacity of version 10 at EC level M. */
const MAX_BYTES = 213

export function Controls({ tl, text, error, qr, pairs, onText }: Props) {
  const [progress, setProgress] = useState(tl.progress())
  const [revealing, setRevealing] = useState(false)

  useEffect(() => {
    tl.eventCallback('onUpdate', () => setProgress(tl.progress()))
    return () => void tl.eventCallback('onUpdate', null)
  }, [tl])

  const svgHref = useMemo(() => `data:image/svg+xml,${encodeURIComponent(qrSvg(qr, pairs))}`, [qr, pairs])
  const pngHref = useMemo(() => qrPng(qr, pairs), [qr, pairs])
  const info = useMemo(() => density(text), [text])
  const summary =
    info.label === 'Too long'
      ? `Too long · ${info.bytes} bytes · max ${MAX_BYTES} at v${MAX_VERSION}`
      : `${info.label} · ${info.bytes} bytes${info.version ? ` · v${info.version}` : ''}`

  return (
    <div className="controls">
      <label>
        Text
        <input value={text} onChange={(e) => onText(e.target.value)} aria-invalid={!!error} aria-describedby="text-error" />
      </label>
      <p id="text-error" role="alert" className="error">
        {error}
      </p>
      <p className="density">{summary}</p>
      <div className="meter" aria-hidden="true">
        {LABELS.map((l) => (
          <span key={l} className={l === info.label ? 'active' : undefined} />
        ))}
      </div>
      <div className="row">
        <button
          onClick={() => {
            if (revealing) tl.reverse()
            else tl.play()
            setRevealing(!revealing)
          }}
        >
          {revealing ? 'Grow back' : 'Reveal'}
        </button>
        <label>
          Progress
          <input
            type="range"
            min={0}
            max={1}
            step={0.001}
            value={progress}
            onChange={(e) => tl.pause().progress(Number(e.target.value))}
          />
        </label>
        <a href={svgHref} download="seasonal-qr.svg">
          Download SVG
        </a>
        <a href={pngHref} download="seasonal-qr.png">
          Download PNG
        </a>
      </div>
    </div>
  )
}
