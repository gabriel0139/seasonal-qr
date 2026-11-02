import { advance, type RootState } from '@react-three/fiber'
import { BufferTarget, CanvasSource, getFirstEncodableVideoCodec, Mp4OutputFormat, Output, QUALITY_HIGH, WebMOutputFormat } from 'mediabunny'
import { Vector2 } from 'three'

const FPS = 30
const REVEAL = 5 * FPS // always the full 5 s reveal, even under reduced motion: it is a file, not motion on screen
const HOLD = 2 * FPS // scan-ready tail (plan §9: hold ≥ 2 s)
const SIZE = 1080

/** Filled by QrScene. While `size` is set, its Rig frames the scan-ready view for a size × size buffer. */
export const capture: { size: number; root?: RootState } = { size: 0 }

/** Renders the reveal at a fixed timestep (plan §19) and downloads it; false if this browser cannot encode video. */
export async function exportVideo(tl: gsap.core.Timeline, onProgress: (fraction: number) => void): Promise<boolean> {
  const root = capture.root
  // H.264/MP4 where the browser has it (Chrome, Safari); Playwright's Chromium has only VP9, so WebM.
  const codec = typeof VideoEncoder === 'undefined' ? null : await getFirstEncodableVideoCodec(['avc', 'vp9'], { width: SIZE, height: SIZE })
  if (!codec || !root) return false

  const { gl, setFrameloop } = root
  const before = { progress: tl.progress(), paused: tl.paused(), reversed: tl.reversed(), dpr: gl.getPixelRatio(), size: gl.getSize(new Vector2()) }
  const output = new Output({ format: codec === 'avc' ? new Mp4OutputFormat({ fastStart: 'in-memory' }) : new WebMOutputFormat(), target: new BufferTarget() })
  const source = new CanvasSource(gl.domElement, { codec, quality: QUALITY_HIGH })
  output.addVideoTrack(source, { frameRate: FPS })

  tl.pause()
  setFrameloop('never') // we drive frames with advance(); this also zeroes the clock, so ambient motion starts at t = 0
  gl.setPixelRatio(1)
  gl.setSize(SIZE, SIZE, false)
  capture.size = SIZE
  try {
    await output.start()
    const frames = REVEAL + HOLD
    for (let i = 0; i < frames; i++) {
      tl.progress(Math.min(1, i / (REVEAL - 1)))
      advance(i / FPS) // runs every useFrame with a 1/FPS delta; Rig renders the frame
      await source.add(i / FPS, 1 / FPS)
      onProgress(i / frames)
    }
    await output.finalize()
  } catch (e) {
    await output.cancel()
    throw e
  } finally {
    capture.size = 0
    gl.setPixelRatio(before.dpr)
    gl.setSize(before.size.x, before.size.y, false)
    tl.progress(before.progress).reversed(before.reversed).paused(before.paused)
    setFrameloop('always')
  }

  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([output.target.buffer!], { type: output.format.mimeType }))
  a.download = `seasonal-qr${output.format.fileExtension}`
  a.click()
  setTimeout(() => URL.revokeObjectURL(a.href), 60_000)
  return true
}
