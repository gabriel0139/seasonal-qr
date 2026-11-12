// Meshopt-compresses dist/models/*.glb in place (public/ stays raw for tree-import, tests and Blender checks)
// and keeps the untouched originals in dist/downloads/ for people who want the models: Blender cannot import Meshopt.
import { mkdir, readdir, readFile, writeFile } from 'node:fs/promises'
import { gzipSync } from 'node:zlib'
import assert from 'node:assert/strict'
import { Logger, NodeIO } from '@gltf-transform/core'
import { EXTMeshoptCompression, KHRMeshQuantization } from '@gltf-transform/extensions'
import { meshopt } from '@gltf-transform/functions'
import { MeshoptDecoder, MeshoptEncoder } from 'meshoptimizer'

const dir = new URL('../dist/models/', import.meta.url)
const downloads = new URL('../dist/downloads/', import.meta.url)
await mkdir(downloads, { recursive: true })
await Promise.all([MeshoptDecoder.ready, MeshoptEncoder.ready])
const io = new NodeIO()
  .setLogger(new Logger(Logger.Verbosity.WARN)) // silences prune chatter
  .registerExtensions([EXTMeshoptCompression, KHRMeshQuantization])
  .registerDependencies({ 'meshopt.decoder': MeshoptDecoder, 'meshopt.encoder': MeshoptEncoder })

/** What Scenery.tsx looks up by name, plus triangle count. */
function summary(doc) {
  const root = doc.getRoot()
  let tris = 0
  for (const mesh of root.listMeshes())
    for (const p of mesh.listPrimitives()) {
      const idx = p.getIndices()
      tris += (idx ? idx.getCount() : p.getAttribute('POSITION').getCount()) / 3
      assert(p.getAttribute('NORMAL'), `${mesh.getName()}: normals lost`)
    }
  const alpha = root.listMaterials().map((m) => `${m.getName()}:${m.getAlphaMode()}:${m.getAlpha()}`).sort()
  return {
    roots: root.listScenes().flatMap((s) => s.listChildren().map((n) => n.getName())).sort(),
    nodes: root.listNodes().map((n) => n.getName()).sort(),
    materials: root.listMaterials().map((m) => m.getName()).sort(),
    alpha,
    tris,
  }
}

const rows = []
for (const f of (await readdir(dir)).filter((f) => f.endsWith('.glb')).sort()) {
  const file = new URL(f, dir)
  const raw = await readFile(file)
  await writeFile(new URL(f, downloads), raw)
  const before = summary(await io.readBinary(raw))
  const doc = await io.readBinary(raw)
  await doc.transform(meshopt({ encoder: MeshoptEncoder, level: 'high' }))
  const out = await io.writeBinary(doc)
  await writeFile(file, out)
  assert.deepEqual(summary(await io.readBinary(await readFile(file))), before, `${f}: compressed output differs from source`)
  rows.push({ file: f, 'raw KB': Math.round(raw.length / 1024), 'out KB': Math.round(out.length / 1024), 'raw gzip KB': Math.round(gzipSync(raw).length / 1024), 'out gzip KB': Math.round(gzipSync(out).length / 1024) })
}
assert(rows.length, 'no models in dist/models')
console.table(rows)
