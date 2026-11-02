import { expect, test } from 'vitest'
import { seasons } from '../../src/seasons'

test.each(Object.values(seasons))('$id has 8 slot classes', (s) => {
  expect(s.tree).toHaveLength(8)
  expect(s.finalDark).toHaveLength(8)
})

// Decoders threshold locally: a dark colour much lighter than its dark neighbours reads as light
// (autumn's amber failed next to the near-black bark). Keep darks in one band and well below the light.
const luma = (c: string) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16)).reduce((s, v, i) => s + v * [0.299, 0.587, 0.114][i], 0)

test.each(Object.values(seasons))('$id darks are deep and within one brightness band', (s) => {
  // Empirical bounds from the Playwright matrix, which stays the real gate: sakura (40..86) scans,
  // autumn's first palette (31..79) did not.
  const darks = s.finalDark.map(luma)
  expect(Math.min(...darks)).toBeGreaterThanOrEqual(38)
  expect(Math.max(...darks) - Math.min(...darks)).toBeLessThanOrEqual(50)
  expect(Math.max(...darks)).toBeLessThanOrEqual(0.4 * luma(s.finalLight))
})
