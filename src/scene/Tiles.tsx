import { useEffect, useMemo } from 'react'
import { BoxGeometry, Color, InstancedBufferAttribute, ShaderMaterial } from 'three'
import type { TilePair } from '../mapping'

// Sakura palette, indexed by Slot.paletteIndex: trunk/branches, deeper pink, blossom, pale blossom.
export const PALETTE = ['#5c3d2e', '#d9739b', '#efa3c0', '#f9d4e2'].map((c) => new Color(c))
const DARK = new Color('#1a1a1a')
const LIGHT = new Color('#ffffff')

const vertexShader = /* glsl */ `
  attribute vec3 aStart;
  attribute vec3 aEnd;
  attribute float aDelay;
  attribute vec3 aStartColor;
  attribute vec3 aEndColor;
  uniform float uProgress;
  varying vec3 vColor;
  void main() {
    float t = clamp((uProgress - aDelay) / (1.0 - aDelay), 0.0, 1.0);
    t = t * t * (3.0 - 2.0 * t);
    float e = t - 1.0; // back-out on the eased t: ~4% overshoot, exactly aEnd at t = 1
    vec3 p = mix(aStart, aEnd, 1.0 + e * e * (2.0 * e + 1.0)) + position;
    p.y += sin(t * 3.14159265) * 2.0; // arc so tiles fly rather than slide
    vColor = mix(aStartColor, aEndColor, t);
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
    () => new ShaderMaterial({ uniforms: { uProgress: progress }, vertexShader, fragmentShader }),
    [progress],
  )

  const geometry = useMemo(() => {
    const n = pairs.length
    const c = (gridSize - 1) / 2
    const start = new Float32Array(n * 3)
    const end = new Float32Array(n * 3)
    const delay = new Float32Array(n)
    const startColor = new Float32Array(n * 3)
    const endColor = new Float32Array(n * 3)
    pairs.forEach(({ slot, cell, delay: d }, i) => {
      start.set([slot.x, slot.y, slot.z], i * 3)
      // Grid centred on the origin, one module per world unit; dark modules land raised.
      end.set([cell.col - c, cell.dark ? 0.5 : 0, cell.row - c], i * 3)
      delay[i] = d
      PALETTE[slot.paletteIndex % PALETTE.length].toArray(startColor, i * 3)
      const finalColor = cell.dark ? DARK : LIGHT
      finalColor.toArray(endColor, i * 3)
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
