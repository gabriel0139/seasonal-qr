import { useGLTF } from '@react-three/drei'
import { useFrame } from '@react-three/fiber'
import { useLayoutEffect, useMemo, useRef } from 'react'
import { Box3, DoubleSide, type Group, type InstancedMesh, MathUtils, MeshBasicMaterial, type Mesh, type MeshStandardMaterial, Object3D } from 'three'
import { seededRandom } from '../mapping'
import { PALETTE } from './Tiles'

const PETALS = 200
const petalMaterial = new MeshBasicMaterial({ side: DoubleSide, transparent: true })
const dummy = new Object3D()

interface Props {
  progress: { value: number }
}

/** The sculpted tree and base plus falling petals for the tree view. Never part of the QR: faded out, then hidden in the scan-ready frame (plan §5.6). */
export function Scenery({ progress }: Props) {
  const { scene } = useGLTF('/models/sakura.glb')
  // Multi-material meshes load as groups of meshes, so collect materials per named part.
  const parts = useMemo(() => {
    const get = (name: string) => {
      const materials: MeshStandardMaterial[] = []
      scene.getObjectByName(name)!.traverse((o) => {
        const mesh = o as Mesh
        if (!mesh.isMesh) return
        const material = mesh.material as MeshStandardMaterial // mutated in place: useMemo runs twice in StrictMode
        material.transparent = true
        materials.push(material)
      })
      return { object: scene.getObjectByName(name)!, materials }
    }
    // Props is absent in older assets. Shared materials are deduped; each keeps its exported opacity as the fade baseline.
    const props = new Set<MeshStandardMaterial>()
    scene.getObjectByName('Props')?.traverse((o) => {
      const mesh = o as Mesh
      if (mesh.isMesh) for (const m of [mesh.material].flat() as MeshStandardMaterial[]) props.add(m)
    })
    const base = get('Base')
    // The pond bowl is cut into the base: fade it with the water so no hole shows under the landing tiles.
    const pondBed = base.materials.find((m) => m.name === 'PondBed')
    if (pondBed) props.add(base.materials.splice(base.materials.indexOf(pondBed), 1)[0])
    const baseline = new Map([...props].map((m) => [m, m.opacity]))
    for (const m of props) m.transparent = true
    const water = scene.getObjectByName('Water')
    const blossoms = get('Blossoms')
    const canopy = new Box3().setFromObject(blossoms.object)
    return { wood: get('Trunk'), blossoms, base, propsRoot: scene.getObjectByName('Props'), baseline, water, waterY: water?.position.y ?? 0, canopy }
  }, [scene])
  const group = useRef<Group>(null!)
  const petals = useRef<InstancedMesh>(null!)
  const seeds = useMemo(() => {
    const rand = seededRandom(7)
    return Array.from({ length: PETALS }, () => [rand(), rand(), rand(), rand()])
  }, [])

  useLayoutEffect(() => {
    for (let i = 0; i < PETALS; i++) petals.current.setColorAt(i, PALETTE[1 + (i % 3)])
  }, [])

  // Ambient only (plan §4.1): driven by clock time, and by progress just for the fade.
  useFrame(({ clock }) => {
    const fade = 1 - MathUtils.smoothstep(progress.value, 0.6, 0.95)
    group.current.visible = fade > 0
    if (!fade) return
    petalMaterial.opacity = fade
    for (const m of parts.base.materials) m.opacity = fade
    // The tiles start inside the tree; dissolving it first reveals them as they fly out.
    const tree = 1 - MathUtils.smoothstep(progress.value, 0, 0.35)
    for (const { object, materials } of [parts.wood, parts.blossoms]) {
      for (const m of materials) m.opacity = tree
      object.visible = tree > 0
    }
    const t = clock.elapsedTime
    // Props sit on the base where the tiles land, so they must be gone by the time the tiles arrive.
    const props = 1 - MathUtils.smoothstep(progress.value, 0.15, 0.5)
    if (parts.propsRoot) parts.propsRoot.visible = props > 0
    for (const [m, o] of parts.baseline) m.opacity = o * props * (m.name === 'Water' ? 1 + 0.08 * Math.sin(t * 1.3) : 1)
    if (parts.water) parts.water.position.y = parts.waterY + 0.05 * Math.sin(t * 0.9)
    // Petals fall from the canopy, which is off-centre on the base.
    const { min, max } = parts.canopy
    const r = Math.max(max.x - min.x, max.z - min.z) / 2
    seeds.forEach(([a, b, c, d], i) => {
      const angle = a * 2 * Math.PI + t * 0.15 // slow swirl around the trunk
      const radius = Math.sqrt(b) * r
      const y = max.y * (1 - ((t * (0.04 + 0.04 * d) + c) % 1))
      dummy.position.set((min.x + max.x) / 2 + Math.cos(angle) * radius + Math.sin(t + d * 6), y, (min.z + max.z) / 2 + Math.sin(angle) * radius)
      dummy.rotation.set(t * (1 + d) + c * 6, t * 0.6 + a * 6, 0)
      dummy.updateMatrix()
      petals.current.setMatrixAt(i, dummy.matrix)
    })
    petals.current.instanceMatrix.needsUpdate = true
  })

  return (
    <group ref={group}>
      {/* base top at y = 0 in the model, so y = -0.5 puts it flush with the bottoms of the landed light tiles */}
      <primitive object={scene} position-y={-0.5} />
      <instancedMesh ref={petals} args={[undefined, petalMaterial, PETALS]} frustumCulled={false}>
        <planeGeometry args={[0.6, 0.4]} />
      </instancedMesh>
    </group>
  )
}
