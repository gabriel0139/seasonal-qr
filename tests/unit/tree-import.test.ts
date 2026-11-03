import { readFileSync } from 'node:fs'
import { expect, test } from 'vitest'
// @ts-expect-error the tool is plain .mjs without type declarations
import { sampleTree } from '../../tools/tree-import.mjs'

const perClass = (slots: number[][]) => [0, 1, 2, 3, 4, 5, 6, 7].map((c) => slots.filter((s) => s[3] === c).length)

// The no-Blender path must sample the shipped model the way the Blender build did (sampleTree also runs its self-checks).
test('tree:import samples sakura.glb like tools/tree-build', async () => {
  const ref = JSON.parse(readFileSync('public/trees/sakura.json', 'utf8'))
  const out = await sampleTree(readFileSync('public/models/sakura.glb'), 'sakura')
  expect(out.slots).toHaveLength(ref.slots.length)
  const want = perClass(ref.slots)
  perClass(out.slots).forEach((n, c) => expect(Math.abs(n - want[c]), `class ${c}: ${n} vs ${want[c]}`).toBeLessThanOrEqual(10))
  for (const hex of out.palette) expect(hex).toMatch(/^#[0-9a-f]{6}$/)
  expect(out.palette).toEqual(ref.palette)
}, 60_000)
