// Ships a season without Blender: copies a GLB to public/models/<id>.glb and samples its slot cloud to
// public/trees/<id>.json with the rules of tools/tree-build/diorama.py (GLB space, so Blender z is y here).
// Usage: npm run tree:import -- <id> <path/to/model.glb>
import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import { pathToFileURL } from 'node:url'
import { Box3, BufferAttribute, BufferGeometry, DoubleSide, Ray, Triangle, Vector3 } from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
// the ESM source: the package `main` is a UMD build that loads a second, CommonJS copy of three
import { MeshBVH } from 'three-mesh-bvh/src/index.js'

const SEED = 1
const N_LAWN = 3000, N_SOLID = 2000
const TRIES = 1e6 // a class with nothing found in this many tries has no room
const SHARES = { 0: 0.08, 5: 0.08, 6: 0.1, 7: 0.04 } // of the non-lawn slots; the canopy takes the rest
const MARGIN_TRUNK = 0.3, MARGIN_CANOPY = 0.6, MARGIN_PROP = 0.5, MARGIN_LAWN = 0.6, POND_CLEAR = 1.0
// diorama.py's three skewed parity rays, Blender (x, y, z) -> GLB (x, z, -y); all point up
const DIRS = [[1, 0.37, 0.21], [-0.29, 1, 0.43], [0.31, -0.17, 1]].map(([x, y, z]) => new Vector3(x, z, -y).normalize())
const UP = new Vector3(0, 1, 0)

function seededRandom(seed) { // mulberry32, as in src/mapping
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

// world-space triangles (9 floats each), one entry per mesh under obj
// shortcut: reads float positions only; a quantized GLB (KHR_mesh_quantization) fails the base-top check, dequantize it first
const meshes = (obj) => {
  const out = []
  obj?.traverse((o) => {
    if (o.isMesh) out.push({ material: o.material, tris: o.geometry.toNonIndexed().applyMatrix4(o.matrixWorld).attributes.position.array })
  })
  return out
}
const join = (ms) => Float32Array.from(ms.flatMap((m) => Array.from(m.tris)))
const keepTris = (tris, f) => {
  const out = []
  for (let i = 0; i < tris.length; i += 9) if (f(tris.subarray(i, i + 9))) out.push(...tris.subarray(i, i + 9))
  return Float32Array.from(out)
}
const boxOf = (tris) => new Box3().setFromBufferAttribute(new BufferAttribute(tris, 3))
const bvhOf = (tris) => (tris.length ? new MeshBVH(new BufferGeometry().setAttribute('position', new BufferAttribute(tris, 3))) : null)

function weld(tris) { // a vertex id per triangle corner, shared by equal positions (glTF splits vertices at seams)
  const ids = new Map(), out = new Int32Array(tris.length / 3)
  for (let i = 0; i < out.length; i++) {
    const k = `${tris[3 * i]},${tris[3 * i + 1]},${tris[3 * i + 2]}`
    if (!ids.has(k)) ids.set(k, ids.size)
    out[i] = ids.get(k)
  }
  return out
}
function openShare(tris) { // share of edges not matched by a reverse edge: 0 when watertight and consistently wound
  const v = weld(tris), edges = new Map(), K = 2 ** 26
  for (let i = 0; i < v.length; i += 3)
    for (let k = 0; k < 3; k++) edges.set(v[i + k] * K + v[i + (k + 1) % 3], (edges.get(v[i + k] * K + v[i + (k + 1) % 3]) ?? 0) + 1)
  let open = 0
  for (const [e, n] of edges) if (edges.get((e % K) * K + Math.floor(e / K)) !== n) open++
  return open / edges.size
}
function pieces(tris) { // connected pieces: the Blender canopy is several overlapping shells merged into one mesh
  const v = weld(tris), parent = Int32Array.from({ length: v.length }, (_, i) => i), out = new Map()
  const find = (i) => {
    while (parent[i] !== i) i = parent[i] = parent[parent[i]]
    return i
  }
  for (let i = 0; i < v.length; i += 3) {
    parent[find(v[i + 1])] = find(v[i])
    parent[find(v[i + 2])] = find(v[i])
  }
  for (let i = 0; i < v.length; i += 3) {
    const r = find(v[i])
    if (!out.has(r)) out.set(r, [])
    out.get(r).push(...tris.subarray(3 * i, 3 * i + 9))
  }
  return [...out.values()].map((t) => Float32Array.from(t))
}
// the shipped canopies are decimated and keep up to 36 open edges in 250k; the two-test vote absorbs those slits
const assertClosed = (n, tris) => {
  const f = openShare(tris)
  assert(f <= 1e-3, `${n}: mesh is not closed, ${(100 * f).toFixed(2)}% of its edges are open or inconsistently wound (at most 0.1%)`)
}

const hit = {}, tri = new Triangle(), nor = new Vector3(), tmp = new Vector3(), ray = new Ray()
const dist = (bvh, p) => bvh.closestPointToPoint(p, hit).distance
function depth(bvh, p) { // distance to the nearest face, negative when p is in front of it (outside)
  const d = dist(bvh, p), index = bvh.geometry.index, f = 3 * hit.faceIndex
  tri.setFromAttributeAndIndices(bvh.geometry.attributes.position, index.getX(f), index.getX(f + 1), index.getX(f + 2)).getNormal(nor)
  return nor.dot(tmp.subVectors(hit.point, p)) > 0 ? d : -d
}
function parityInside(bvh, p) { // majority vote of ray parity along the three skewed directions
  let votes = 0
  for (const d of DIRS) {
    // a ray through a shared edge hits both triangles: count hits 1e-4 apart, like diorama.py's step-past loop
    const t = bvh.raycast(ray.set(p, d), DoubleSide).map((h) => h.distance).sort((a, b) => a - b)
    votes += t.filter((x, i) => !i || x - t[i - 1] > 1e-4).length & 1
  }
  return votes >= 2
}
// both tests must agree: decimated meshes fold a few triangles, fooling either alone
const inside = (p, bvhs, margin) => bvhs.some((b) => b.geometry.boundingBox.containsPoint(p) && depth(b, p) >= margin && parityInside(b, p))
const clear = (p, bvhs, margin) => bvhs.every((b) => dist(b, p) >= margin && !parityInside(b, p))
const under = (bvh, p) => !!bvh.raycastFirst(ray.set(p, UP), DoubleSide)

const luma = (hex) => [1, 3, 5].reduce((s, i, k) => s + parseInt(hex.slice(i, i + 2), 16) * [0.299, 0.587, 0.114][k], 0)
const toHex = (m) => // linear base colour factor -> sRGB hex, as diorama.py's to_hex
  '#' + m.color.toArray().map((x) => Math.round(255 * (x <= 0.0031308 ? x * 12.92 : 1.055 * x ** (1 / 2.4) - 0.055)).toString(16).padStart(2, '0')).join('')
function largest(ms, keep = () => true) { // the material covering the most surface, of the triangles keep() passes
  const area = new Map()
  for (const { material, tris } of ms)
    for (let i = 0; i < tris.length; i += 9) {
      tri.set(tri.a.fromArray(tris, i), tri.b.fromArray(tris, i + 3), tri.c.fromArray(tris, i + 6))
      if (keep(tri)) area.set(material, (area.get(material) ?? 0) + tri.getArea())
    }
  return [...area].sort((a, b) => b[1] - a[1])[0][0]
}

/** Validates the GLB node contract, samples the slot cloud, runs the self-checks and returns the slot JSON. */
export async function sampleTree(glb, name) {
  const { scene } = await new GLTFLoader().parseAsync(glb.buffer.slice(glb.byteOffset, glb.byteOffset + glb.byteLength), '')
  scene.updateMatrixWorld(true)
  const part = (o) => {
    const ms = meshes(o), tris = join(ms)
    return ms.length ? { ms, tris, box: boxOf(tris) } : null
  }
  const roots = Object.fromEntries(scene.children.map((o) => [o.name, o]))
  const tree = {}
  for (const n of ['Trunk', 'Blossoms', 'Base']) {
    assert(roots[n], `${n}: missing root node (the scene needs Trunk, Blossoms and Base; found ${Object.keys(roots).join(', ') || 'none'})`)
    assert((tree[n] = part(roots[n])), `${n}: has no triangle mesh`)
    assertClosed(n, tree[n].tris)
  }
  const { Trunk, Blossoms, Base } = tree
  assert(Math.abs(Base.box.max.y) <= 0.01, `Base: top must be at y = 0, found y = ${Base.box.max.y.toFixed(3)} (is the model Y up?)`)
  assert(Blossoms.box.max.y > 0, 'Blossoms: must rise above the base top (is the model Y up?)')
  assert(Math.max(-Base.box.min.x, Base.box.max.x, -Base.box.min.z, Base.box.max.z) <= 36.001, 'Base: x and z must stay within ±36')

  const props = Object.fromEntries((roots.Props?.children ?? []).map((o) => [o.name, part(o)]).filter(([, p]) => p))
  for (const n of ['Bridge', 'Lantern', 'Rocks']) if (props[n]) assertClosed(n, props[n].tris) // their classes sample inside them
  // inside any one shell, as diorama.py tests the shells: inside two overlapping ones has even ray parity
  const trunk = bvhOf(Trunk.tris), canopy = pieces(Blossoms.tris).map(bvhOf)
  // the top tier only, as in diorama.py: faces hidden inside the slab (a lower tier's top) would be the nearest surface
  const base = bvhOf(keepTris(Base.tris, (t) => Math.max(t[1], t[4], t[7]) > -3.0))
  const bed = bvhOf(join(Base.ms.filter((m) => m.material.name === 'PondBed')))
  // Water is an open disc: parity through it means nothing, so it is no obstacle
  const solid = Object.entries(props).filter(([k]) => k !== 'Water').map(([, p]) => bvhOf(p.tris))
  const wood = [props.Bridge].filter(Boolean), stone = [props.Lantern, props.Rocks].filter(Boolean), water = props.Water
  const woodB = wood.map((p) => bvhOf(p.tris)), stoneB = stone.map((p) => bvhOf(p.tris)), waterB = water && bvhOf(water.tris)

  const rules = (e) => { // class -> slot test; e loosens the margins to re-test the rounded slots
    const r = {
      0: (p) => p.y >= 0.3 - e && inside(p, [trunk], MARGIN_TRUNK - e),
      1: (p) => inside(p, canopy, MARGIN_CANOPY - e),
      4: (p) => p.y >= -2.2 - e && p.y <= -0.6 + e && (!bed || (dist(bed, p) >= POND_CLEAR - e && !under(bed, p)))
        && inside(p, [base], MARGIN_LAWN - e) && clear(p, [trunk, ...solid], MARGIN_PROP - e),
      5: (p) => p.y >= 0.5 - e && inside(p, woodB, MARGIN_PROP - e),
      6: (p) => p.y >= 0.5 - e && inside(p, stoneB, MARGIN_PROP - e),
      // under the surface, off the bed, piers and bank
      7: (p) => under(waterB, p) && dist(waterB, p) >= MARGIN_PROP - e && clear(p, [base, ...solid], MARGIN_PROP - e),
    }
    r[2] = r[3] = r[1]
    return r
  }

  const rand = seededRandom(SEED)
  function sample(box, count, ok, ylo, yhi) { // uniform rejection sampling in the box
    const { min, max } = box.clone()
    if (ylo !== undefined) min.y = ylo
    if (yhi !== undefined) max.y = yhi
    const out = []
    for (let n = 0; out.length < count && n < TRIES; n++) {
      const p = new Vector3(min.x + rand() * (max.x - min.x), min.y + rand() * (max.y - min.y), min.z + rand() * (max.z - min.z))
      if (ok(p)) out.push(p)
    }
    return out
  }
  const need = (pts, n, what) => {
    assert.equal(pts.length, n, `${what}: found ${pts.length} of ${n} slots in ${TRIES} tries (closed, and thick enough?)`)
    return pts
  }

  const RULE = rules(0), want = Object.fromEntries(Object.entries(SHARES).map(([c, s]) => [c, Math.round(N_SOLID * s)]))
  const pts = {
    0: need(sample(Trunk.box, want[0], RULE[0], 0.3), want[0], `Trunk (>= ${MARGIN_TRUNK} deep, y >= 0.3)`),
    // a prop class with no room gets no slots and its share goes to the canopy; partial fills fail the check below
    5: wood.length ? sample(wood[0].box, want[5], RULE[5], 0.5) : [],
    6: stone.length ? sample(stone.reduce((b, p) => b.union(p.box), new Box3()), want[6], RULE[6], 0.5) : [],
    7: water ? sample(water.box, want[7], RULE[7], Base.box.min.y) : [],
  }
  const nCanopy = N_SOLID - pts[0].length - pts[5].length - pts[6].length - pts[7].length
  const bloom = need(sample(Blossoms.box, nCanopy, RULE[1]), nCanopy, `Blossoms (>= ${MARGIN_CANOPY} deep)`)
  pts[4] = need(sample(Base.box, N_LAWN, RULE[4], -2.2, -0.6), N_LAWN, `Base lawn (>= ${MARGIN_LAWN} deep, y in [-2.2, -0.6], clear of trunk, props and pond)`)

  // shade: distance from the canopy's bottom centre, so 3 (palest) lands upper/outer and 1 (deepest) lower/inner
  const cx = bloom.reduce((s, p) => s + p.x, 0) / bloom.length, cz = bloom.reduce((s, p) => s + p.z, 0) / bloom.length
  const ylo = Math.min(...bloom.map((p) => p.y)), yhi = Math.max(...bloom.map((p) => p.y))
  const rmax = Math.max(...bloom.map((p) => Math.hypot(p.x - cx, p.z - cz)))
  const gauss = () => Math.sqrt(-2 * Math.log(1 - rand())) * Math.cos(2 * Math.PI * rand())
  const score = bloom.map((p) => Math.hypot(Math.hypot(p.x - cx, p.z - cz) / rmax, (p.y - ylo) / (yhi - ylo)) + 0.08 * gauss())
  pts[1] = []; pts[2] = []; pts[3] = []
  bloom.map((_, i) => i).sort((a, b) => score[a] - score[b])
    .forEach((i, r) => pts[r < 0.3 * bloom.length ? 1 : r < 0.7 * bloom.length ? 2 : 3].push(bloom[i]))

  // one seeded shuffle, stratified: class c's i-th slot (already in random order) gets key (i + u) / n_c, so any
  // prefix keeps the class proportions and covers each volume evenly
  const keyed = Object.entries(pts).flatMap(([c, ps]) => ps.map((p, i) => [(i + rand()) / ps.length, +c, p]))
  const r2 = (v) => Math.round(v * 100) / 100 + 0 // + 0 turns -0 into 0
  const slots = keyed.sort((a, b) => a[0] - b[0]).map(([, c, p]) => [r2(p.x), r2(p.y), r2(p.z), c])

  const canopyHex = [...new Set(Blossoms.ms.map((m) => toHex(m.material)))].sort((a, b) => luma(a) - luma(b))
  const first = (p) => p && toHex(p.ms[0].material)
  const trunkHex = toHex(largest(Trunk.ms))
  // the lawn is the base's top: by area or triangle count its stone sides, bottom or rock chunks win
  const lawnHex = toHex(largest(Base.ms, (t) => t.getNormal(nor).y > 0.5))
  const palette = [trunkHex, canopyHex[0], canopyHex[1] ?? canopyHex[0], canopyHex.at(-1), lawnHex,
    first(wood[0]) ?? trunkHex, first(stone[0]) ?? '#3d4049', first(water) ?? '#173f66']
  let half = 0
  for (let i = 0; i < Base.tris.length; i += 3) if (Base.tris[i + 1] > -3.0) half = Math.max(half, Math.abs(Base.tris[i]), Math.abs(Base.tris[i + 2]))

  // self-check: every rounded slot passes its class test again
  const R = rules(0.02)
  for (const [x, y, z, c] of slots) assert(R[c](new Vector3(x, y, z)), `slot fails its class test: ${[x, y, z, c]}`)
  // self-check: counts, shares and prefixes (a version 10 grid needs about 1,650 dark and 2,575 light cells)
  const P = slots.map((s) => s[3])
  const n = [0, 1, 2, 3, 4, 5, 6, 7].map((c) => P.filter((x) => x === c).length)
  assert(n[4] === N_LAWN && P.length - n[4] === N_SOLID, `slot counts ${n}`)
  assert(n[0] === want[0] && [5, 6, 7].every((c) => n[c] === 0 || n[c] === want[c]), `prop classes partly filled: ${n}, want ${JSON.stringify(want)}`)
  const nc = n[1] + n[2] + n[3]
  assert([[1, 0.3], [2, 0.4], [3, 0.3]].every(([c, s]) => Math.abs(n[c] - s * nc) <= 1), `canopy split ${n}`)
  for (const T of [1089, 2025, 4225])
    for (let c = 0; c < 8; c++) assert(Math.abs(P.slice(0, T).filter((x) => x === c).length / T - n[c] / P.length) < 0.02, `prefix ${T} loses the class mix (class ${c})`)

  return { name, baseSize: r2(2 * half), palette, slots }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [id, src] = process.argv.slice(2)
  try {
    if (!/^[a-z0-9-]+$/.test(id ?? '') || !src) throw new Error('usage: npm run tree:import -- <id> <path/to/model.glb> (id: lowercase letters, digits and dashes)')
    const glb = readFileSync(src)
    const json = await sampleTree(glb, id)
    writeFileSync(new URL(`../public/models/${id}.glb`, import.meta.url), glb)
    writeFileSync(new URL(`../public/trees/${id}.json`, import.meta.url), JSON.stringify(json))
    const n = [0, 1, 2, 3, 4, 5, 6, 7].map((c) => json.slots.filter((s) => s[3] === c).length)
    console.log(`public/models/${id}.glb, public/trees/${id}.json: ${json.slots.length} slots, per class ${n.join(' ')}`)
    console.log(`baseSize ${json.baseSize}, palette ${json.palette.join(' ')}`)
  } catch (err) {
    console.error(`tree:import failed: ${err.message}`)
    process.exitCode = 1
  }
}
