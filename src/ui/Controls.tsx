import { useEffect, useMemo, useState } from 'react'
import { QUIET_ZONE, type QrResult } from '../qr'

interface Props {
  tl: gsap.core.Timeline
  text: string
  error: string | null
  qr: QrResult
  onText: (text: string) => void
}

/** Flat SVG of the same matrix the tiles show (plan §5.9 fallback). */
function qrSvg({ size, modules }: QrResult): string {
  const g = size + 2 * QUIET_ZONE
  let d = ''
  modules.forEach((m, i) => {
    if (m) d += `M${(i % size) + QUIET_ZONE} ${Math.floor(i / size) + QUIET_ZONE}h1v1h-1z`
  })
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${g} ${g}" shape-rendering="crispEdges"><rect width="${g}" height="${g}" fill="#fff"/><path d="${d}" fill="#1a1a1a"/></svg>`
}

export function Controls({ tl, text, error, qr, onText }: Props) {
  const [progress, setProgress] = useState(tl.progress())
  const [revealing, setRevealing] = useState(false)

  useEffect(() => {
    tl.eventCallback('onUpdate', () => setProgress(tl.progress()))
    return () => void tl.eventCallback('onUpdate', null)
  }, [tl])

  const svgHref = useMemo(() => `data:image/svg+xml,${encodeURIComponent(qrSvg(qr))}`, [qr])

  return (
    <div className="controls">
      <label>
        Text
        <input value={text} onChange={(e) => onText(e.target.value)} aria-invalid={!!error} aria-describedby="text-error" />
      </label>
      <p id="text-error" role="alert" className="error">
        {error}
      </p>
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
      </div>
    </div>
  )
}
