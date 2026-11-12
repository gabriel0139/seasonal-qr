import { Canvas, useFrame } from '@react-three/fiber'
import { Suspense, useMemo } from 'react'
import { MathUtils, OrthographicCamera, PerspectiveCamera, Vector2, Vector3 } from 'three'
import { capture } from '../export/video'
import type { TilePair } from '../mapping'
import type { Season } from '../seasons'
import { Scenery } from './Scenery'
import { Tiles } from './Tiles'

type Shared = { value: number }

interface Props {
  season: Season
  pairs: TilePair[]
  gridSize: number
  /** device pixels per QR module in the scan-ready frame */
  modulePx: number
  /** uProgress, 0 = tree, 1 = scan-ready QR */
  progress: Shared
  /** camera blend, 0 = tree view, 1 = top-down */
  rig: Shared
}

const END_FOV = 10

export function QrScene(props: Props) {
  const css = (props.gridSize * props.modulePx) / window.devicePixelRatio
  return (
    <div style={{ width: css, height: css }}>
      <Canvas flat shadows="percentage" gl={{ antialias: false, preserveDrawingBuffer: true }} dpr={window.devicePixelRatio} onCreated={(root) => (capture.root = root)}>
        <color attach="background" args={[props.season.finalLight]} />
        <Tiles season={props.season} pairs={props.pairs} gridSize={props.gridSize} progress={props.progress} />
        {/* tree-state lighting only: tiles and petals are unlit, so the scan-ready frame is unaffected */}
        <hemisphereLight args={['#eaf2ff', '#c9b79c', 1.3]} />
        <Suspense fallback={null}>
          <Scenery season={props.season} progress={props.progress} />
        </Suspense>
        <Rig {...props} />
      </Canvas>
    </div>
  )
}

const buffer = new Vector2()
const target = new Vector3()
const orbit = new Vector3()
const HERO = Math.atan2(0.6, 1) // the tree view's azimuth off the front

/** Owns both cameras and renders the frame; the scan-ready frame (progress 1) is always orthographic. */
function Rig({ season, pairs, gridSize, modulePx, progress, rig }: Props) {
  const persp = useMemo(() => new PerspectiveCamera(40, 1, 1, 2000), [])
  // Exactly top-down. Up = -z puts row 0 (smallest z) at the top of the image and col 0 (smallest x) at the left.
  const ortho = useMemo(() => {
    const cam = new OrthographicCamera()
    cam.position.set(0, 100, 0)
    cam.up.set(0, 0, -1)
    cam.lookAt(0, 0, 0)
    cam.near = 1
    cam.far = 200
    return cam
  }, [])

  const poses = useMemo(() => {
    const h = Math.max(...pairs.map((p) => p.slot.y))
    const w = Math.max(...pairs.map((p) => Math.hypot(p.slot.x, p.slot.z)))
    const treeTarget = new Vector3(0, h * 0.45, 0)
    // Narrow-FOV perspective that frames the grid like the ortho camera, so the hard switch barely shows.
    const height = season.baseSize / 2 / Math.tan(MathUtils.degToRad(END_FOV / 2))
    return {
      from: { dist: Math.max(h, w) * 3.4, target: treeTarget, up: new Vector3(0, 1, 0), fov: 40 },
      to: { pos: new Vector3(0, 0.5 + height, 0), target: new Vector3(0, 0.5, 0), up: new Vector3(0, 0, -1), fov: END_FOV },
    }
  }, [pairs, gridSize, season])

  useFrame(({ gl, scene }) => {
    const done = progress.value >= 1
    if (done) {
      // Offset the grid's top-left edge by whole pixels so modules start on whole device pixels,
      // even if the drawing buffer rounds a pixel off; any excess is letterboxed in the background colour.
      gl.getDrawingBufferSize(buffer)
      const px = capture.size ? Math.floor(capture.size / gridSize) : modulePx
      const s = season.baseSize / gridSize // world size of one module
      const margin = (n: number) => (Math.max(0, Math.floor((n - gridSize * px) / 2)) / px) * s // whole-pixel letterbox; 0 on the live canvas
      ortho.left = -season.baseSize / 2 - margin(buffer.x)
      ortho.right = ortho.left + (buffer.x / px) * s
      ortho.top = season.baseSize / 2 + margin(buffer.y)
      ortho.bottom = ortho.top - (buffer.y / px) * s
      ortho.updateProjectionMatrix()
    } else {
      const { from, to } = poses
      const k = rig.value
      // Orbit to the front during the unfold, so the rise to top-down is a straight lift with no roll.
      const a = HERO * (1 - MathUtils.smootherstep(progress.value, 0.05, 0.75))
      orbit.set(Math.sin(a) * Math.hypot(0.6, 1), 0.4, Math.cos(a) * Math.hypot(0.6, 1)).setLength(from.dist).add(from.target)
      persp.position.lerpVectors(orbit, to.pos, k)
      persp.up.lerpVectors(from.up, to.up, k).normalize()
      persp.lookAt(target.lerpVectors(from.target, to.target, k))
      persp.fov = MathUtils.lerp(from.fov, to.fov, k)
      persp.updateProjectionMatrix()
    }
    gl.render(scene, done ? ortho : persp)
    // Flag only after the scan-ready frame has actually been drawn (docs-contract.md).
    const ready = String(done)
    if (document.body.dataset.ready !== ready) document.body.dataset.ready = ready
  }, 1)

  return null
}
