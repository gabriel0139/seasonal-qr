import { existsSync, readFileSync } from 'node:fs'
import { expect, test } from 'vitest'
import { seasons } from '../../src/seasons'
import { deriveSeason, hexToRgb, luma, withLuma } from '../../src/seasons/derive'

const file = (id: string) => `public/trees/${id}.json`
// Seasons without a slot JSON yet are skipped.
const derived = Object.values(seasons)
  .filter((e) => existsSync(file(e.id)))
  .map((e) => {
    const json = JSON.parse(readFileSync(file(e.id), 'utf8'))
    return deriveSeason(e.id, e.name, { palette: json.palette, baseSize: json.baseSize }, e.overrides)
  })

test.each(derived)('$id has 8 slot classes', (s) => {
  expect(s.tree).toHaveLength(8)
  expect(s.finalDark).toHaveLength(8)
})

// Decoders threshold locally: a dark colour much lighter than its dark neighbours reads as light
// (autumn's amber failed next to the near-black bark). Keep darks in one band and well below the light.
test.each(derived)('$id darks are deep and within one brightness band', (s) => {
  // Empirical bounds from the Playwright matrix, which stays the real gate: sakura (40..86) scans,
  // autumn's first palette (31..79) did not.
  const darks = s.finalDark.map(luma)
  expect(Math.min(...darks)).toBeGreaterThanOrEqual(38)
  expect(Math.max(...darks) - Math.min(...darks)).toBeLessThanOrEqual(50)
  expect(Math.max(...darks)).toBeLessThanOrEqual(0.4 * luma(s.finalLight))
})

const hue = (hex: string) => {
  const [r, g, b] = hexToRgb(hex)
  return (Math.atan2(Math.sqrt(3) * (g - b), 2 * r - g - b) * 180) / Math.PI
}

test.each([
  ['#f9d4e2', 56],
  ['#5aa9e0', 56],
  ['#e8873a', 56],
  ['#ffffff', 56],
  ['#9bc24a', 232],
])('withLuma(%s, %i) hits the target luma and keeps the hue', (hex, target) => {
  const out = withLuma(hex, target, 0.55)
  expect(out).toMatch(/^#[0-9a-f]{6}$/)
  expect(Math.abs(luma(out) - target)).toBeLessThanOrEqual(1)
  if (hex !== '#ffffff') expect(Math.abs(hue(out) - hue(hex))).toBeLessThan(8)
})

test('deriveSeason makes 8 darks at one luma and a pale light', () => {
  const palette = ['#5c3d2e', '#d9739b', '#efa3c0', '#f9d4e2', '#9bc24a', '#b8743f', '#9a9aa6', '#5aa9e0']
  const s = deriveSeason('x', 'X', { palette, baseSize: 50 })
  expect(s.finalDark).toHaveLength(8)
  s.finalDark.forEach((c) => expect(Math.abs(luma(c) - 56)).toBeLessThanOrEqual(1))
  expect(Math.abs(luma(s.finalLight) - 232)).toBeLessThanOrEqual(1)
  expect(s.tree).toEqual(palette)
  expect(s.baseSize).toBe(50)
  expect(s.petals).toEqual([1, 2, 3])
})
