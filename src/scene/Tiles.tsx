import { useEffect, useMemo } from 'react'
import { BoxGeometry, Color, InstancedBufferAttribute, ShaderMaterial } from 'three'
import { FLIGHT, type TilePair } from '../mapping'

import { sakura } from '../seasons/sakura'

const colors = (hex: string[]) => hex.map((c) => new Color(c))
export const PALETTE = colors(sakura.tree)
const FINAL_DARK = colors(sakura.finalDark)
const FINAL_LIGHT = new Color(sakura.finalLight)

const vertexShader = /* glsl */ `
  attribute vec3 aStart;
  attribute vec3 aEnd;
  attribute float aDelay;
  attribute vec3 aStartColor;
  attribute vec3 aEndColor;
  uniform float uProgress;
  uniform float uScale;
  varying vec3 vColor;
  void main() {
    float t = clamp((uProgress - aDelay) / float(FLIGHT), 0.0, 1.0); // every tile flies for FLIGHT, landing at aDelay + FLIGHT
    t = t * t * (3.0 - 2.0 * t);
    float e = t - 1.0; // back-out on the eased t: ~4% overshoot, exactly aEnd at t = 1
    vec3 p = mix(aStart, aEnd, 1.0 + e * e * (2.0 * e + 1.0)) + position * mix(1.0, uScale, t); // 1 unit while hidden in the mesh, exactly uScale once landed
    p.y += sin(t * 3.14159265) * 2.0; // arc so tiles fly rather than slide
    // Lambert from the directional light in QrScene so flying tiles read as boxes; exactly 1 once landed (plan §5.4).
    float shade = 0.65 + 0.35 * max(dot(normal, normalize(vec3(40.0, 80.0, 50.0))), 0.0);
    vColor = mix(aStartColor, aEndColor, t) * mix(shade, 1.0, t);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
  }
`

// Unlit flat colour; colours are mixed in linear space, then converted to the sRGB output.
const fragmentShader = /* glsl */ `
  varying vec3 vColor;
  void main() {
    gl_FragColor = vec4(vColor, 1.0);
    #include <colorspace_fragment>
  }
`

interface Props {
  pairs: TilePair[]
  gridSize: number
  /** shared uniform object, tweened by the GSAP timeline */
  progress: { value: number }
}

export function Tiles({ pairs, gridSize, progress }: Props) {
  const material = useMemo(
    () => new ShaderMaterial({ uniforms: { uProgress: progress, uScale: { value: sakura.baseSize / gridSize } }, defines: { FLIGHT }, vertexShader, fragmentShader }),
    [progress, gridSize],
  )

  const geometry = useMemo(() => {
    const n = pairs.length
    const c = (gridSize - 1) / 2
    const s = sakura.baseSize / gridSize
    const start = new Float32Array(n * 3)
    const end = new Float32Array(n * 3)
    const delay = new Float32Array(n)
    const startColor = new Float32Array(n * 3)
    const endColor = new Float32Array(n * 3)
    pairs.forEach(({ slot, cell, delay: d }, i) => {
      start.set([slot.x, slot.y, slot.z], i * 3)
      // Grid centred on the origin spanning baseSize, bottoms flush on the base top (y = -0.5); dark modules raised s/2.
      end.set([(cell.col - c) * s, s / 2 - 0.5 + (cell.dark ? s / 2 : 0), (cell.row - c) * s], i * 3)
      delay[i] = d
      PALETTE[slot.paletteIndex].toArray(startColor, i * 3)
      ;(cell.dark ? FINAL_DARK[slot.paletteIndex] : FINAL_LIGHT).toArray(endColor, i * 3)
    })
    const g = new BoxGeometry(1, 1, 1) // exact 1×1 footprint: zero gaps between neighbours (plan §5.5)
    g.setAttribute('aStart', new InstancedBufferAttribute(start, 3))
    g.setAttribute('aEnd', new InstancedBufferAttribute(end, 3))
    g.setAttribute('aDelay', new InstancedBufferAttribute(delay, 1))
    g.setAttribute('aStartColor', new InstancedBufferAttribute(startColor, 3))
    g.setAttribute('aEndColor', new InstancedBufferAttribute(endColor, 3))
    return g
  }, [pairs, gridSize])

  useEffect(() => () => geometry.dispose(), [geometry])
  useEffect(() => () => material.dispose(), [material])

  // frustumCulled off: the bounding sphere comes from the (identity) instance matrices, not the shader positions.
  return <instancedMesh args={[geometry, material, pairs.length]} frustumCulled={false} />
}
