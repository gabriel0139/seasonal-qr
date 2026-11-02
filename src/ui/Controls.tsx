import { useEffect, useMemo, useState } from 'react'
import { exportVideo } from '../export/video'
import type { TilePair } from '../mapping'
import { density, MAX_VERSION, QUIET_ZONE, type QrResult } from '../qr'
import { seasons, type Season } from '../seasons'

interface Props {
  season: Season
  seasonError: string | null
  onSeason: (id: string) => void
  tl: gsap.core.Timeline
  text: string
  error: string | null
  qr: QrResult
  pairs: TilePair[]
  onText: (text: string) => void
  seed: number
}

/** Dark modules grouped by mosaic colour, as [col, row] in grid coordinates (quiet zone included). */
function darkByColour(season: Season, pairs: TilePair[]): Map<string, number[][]> {
  const by = new Map<string, number[][]>()
  for (const { cell, slot } of pairs) {
    if (!cell.dark) continue
    const colour = season.finalDark[slot.paletteIndex]
    by.set(colour, [...(by.get(colour) ?? []), [cell.col, cell.row]])
  }
  return by
}

/** Flat SVG of the same mosaic the tiles show (plan §5.9 fallback). */
function qrSvg(season: Season, { size }: QrResult, pairs: TilePair[]): string {
  const g = size + 2 * QUIET_ZONE
  const paths = [...darkByColour(season, pairs)]
    .map(([colour, cs]) => `<path d="${cs.map(([c, r]) => `M${c} ${r}h1v1h-1z`).join('')}" fill="${colour}"/>`)
    .join('')
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${g} ${g}" shape-rendering="crispEdges"><rect width="${g}" height="${g}" fill="${season.finalLight}"/>${paths}</svg>`
}

/** Flat PNG at 10 px per module, same mosaic as qrSvg. */
function qrPng(season: Season, { size }: QrResult, pairs: TilePair[]): string {
  const px = 10
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = (size + 2 * QUIET_ZONE) * px
  const ctx = canvas.getContext('2d')
  if (!ctx) return '' // no canvas support (e.g. jsdom without the canvas package)
  ctx.fillStyle = season.finalLight
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  for (const [colour, cs] of darkByColour(season, pairs)) {
    ctx.fillStyle = colour
    for (const [c, r] of cs) ctx.fillRect(c * px, r * px, px, px)
  }
  return canvas.toDataURL('image/png')
}

const LABELS = ['Short', 'Medium', 'Dense'] as const
/** Byte-mode capacity of version 10 at EC level M. */
const MAX_BYTES = 213

export function Controls({ season, seasonError, onSeason, tl, text, error, qr, pairs, onText, seed }: Props) {
  const [progress, setProgress] = useState(tl.progress())
  const [revealing, setRevealing] = useState(false)
  const [includeText, setIncludeText] = useState(false)
  const [copied, setCopied] = useState(false)
  const [exporting, setExporting] = useState<number | null>(null) // fraction done while a video export runs
  const [videoLabel, setVideoLabel] = useState('Export video')

  async function onExportVideo() {
    setExporting(0)
    try {
      if (!(await exportVideo(tl, setExporting))) setVideoLabel('Video export needs Chrome, Edge or Safari 17+')
    } finally {
      setExporting(null)
    }
  }

  function copyLink() {
    const p = new URLSearchParams({ season: season.id, seed: String(seed) })
    if (includeText) p.set('text', text)
    navigator.clipboard.writeText(`${location.origin}${location.pathname}#${p}`).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  useEffect(() => {
    tl.eventCallback('onUpdate', () => setProgress(tl.progress()))
    return () => void tl.eventCallback('onUpdate', null)
  }, [tl])

  const svgHref = useMemo(() => `data:image/svg+xml,${encodeURIComponent(qrSvg(season, qr, pairs))}`, [season, qr, pairs])
  const pngHref = useMemo(() => qrPng(season, qr, pairs), [season, qr, pairs])
  const info = useMemo(() => density(text), [text])
  const summary =
    info.label === 'Too long'
      ? `Too long · ${info.bytes} bytes · max ${MAX_BYTES} at v${MAX_VERSION}`
      : `${info.label} · ${info.bytes} bytes${info.version ? ` · v${info.version}` : ''}`

  return (
    <div className="controls" inert={exporting !== null}>
      <label>
        Text
        <input value={text} onChange={(e) => onText(e.target.value)} aria-invalid={!!error} aria-describedby="text-error" />
      </label>
      <p id="text-error" role="alert" className="error">
        {error}
      </p>
      <label>
        Season
        <select value={season.id} onChange={(e) => onSeason(e.target.value)}>
          {Object.values(seasons).map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </label>
      {seasonError && (
        <p role="alert" className="error">
          {seasonError}
        </p>
      )}
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
        <label>
          <input type="checkbox" checked={includeText} onChange={(e) => setIncludeText(e.target.checked)} />
          Include text in link
        </label>
        <button onClick={copyLink}>{copied ? 'Copied' : 'Copy link'}</button>
        <button onClick={onExportVideo}>{exporting === null ? videoLabel : `Exporting ${Math.round(exporting * 100)}%`}</button>
      </div>
    </div>
  )
}
