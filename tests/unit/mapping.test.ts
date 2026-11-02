import { describe, expect, it } from 'vitest'
import { cloudSlots, coneSlotCloud, FLIGHT, qrCells, radialUnfold } from '../../src/mapping'
import { encodeQr, gridSize } from '../../src/qr'

const qr = encodeQr('https://github.com/gabrieljohnliew/seasonal-qr')
const cells = qrCells(qr)
const N = gridSize(qr.version)
const slots = coneSlotCloud(cells.length, 1)

describe('coneSlotCloud', () => {
  it('is deterministic per seed with sequential ids', () => {
    expect(coneSlotCloud(500, 7)).toEqual(coneSlotCloud(500, 7))
    expect(coneSlotCloud(500, 7)).not.toEqual(coneSlotCloud(500, 8))
    expect(coneSlotCloud(500, 7).map((s) => s.id)).toEqual([...Array(500).keys()])
  })
})

describe('cloudSlots', () => {
  const cloud = { slots: [[1, 2, 3, 0], [4, 5, 6, 2], [7, 8, 9, 1]] }
  it('takes the first count slots with sequential ids', () => {
    expect(cloudSlots(cloud, 2)).toEqual([
      { id: 0, x: 1, y: 2, z: 3, paletteIndex: 0 },
      { id: 1, x: 4, y: 5, z: 6, paletteIndex: 2 },
    ])
  })
  it('throws when the cloud is too small', () => {
    expect(() => cloudSlots(cloud, 4)).toThrow(/need 4/)
  })
  it('filters by palette index and keeps file-row ids', () => {
    expect(cloudSlots(cloud, 2, (p) => p !== 2).map((s) => s.id)).toEqual([0, 2])
    expect(() => cloudSlots(cloud, 2, (p) => p === 2)).toThrow(/need 2/)
  })
})

describe('qrCells', () => {
  it('covers the full grid with 147 finder cells and matching dark count', () => {
    expect(cells.length).toBe(gridSize(qr.version) ** 2)
    expect(cells.filter((c) => c.finder).length).toBe(147)
    expect(cells.filter((c) => c.dark).length).toBe(qr.modules.reduce((a, b) => a + b, 0))
  })
})

describe('radialUnfold', () => {
  const pairs = radialUnfold(slots, cells, N, 1)
  it('is a bijection', () => {
    expect(new Set(pairs.map((p) => p.cell)).size).toBe(cells.length)
    expect(new Set(pairs.map((p) => p.slot.id)).size).toBe(slots.length)
  })
  it('gives finders delay 0.12 and the highest slots', () => {
    const fin = pairs.filter((p) => p.cell.finder)
    expect(fin.every((p) => p.delay === 0.12)).toBe(true)
    const minFinderY = Math.min(...fin.map((p) => p.slot.y))
    const others = pairs.filter((p) => !p.cell.finder)
    expect(others.every((p) => p.slot.y <= minFinderY)).toBe(true)
  })
  it('keeps non-finder delays in [0.28, 0.74], growing with radius, and is deterministic', () => {
    const rest = pairs.filter((p) => !p.cell.finder)
    expect(rest.every((p) => p.delay >= 0.28 && p.delay <= 0.74)).toBe(true)
    expect(Math.max(...pairs.map((p) => p.delay)) + FLIGHT).toBeLessThanOrEqual(0.92 + 1e-9)
    const c = (N - 1) / 2
    const r = (p: (typeof pairs)[number]) => Math.hypot(p.cell.col - c, p.cell.row - c)
    const byR = [...rest].sort((a, b) => r(a) - r(b))
    const mean = (a: typeof rest) => a.reduce((t, p) => t + p.delay, 0) / a.length
    const q = Math.floor(rest.length / 4)
    expect(mean(byR.slice(0, q))).toBeLessThan(mean(byR.slice(-q)))
    expect(radialUnfold(slots, cells, N, 1)).toEqual(pairs)
  })
  it('rejects length mismatch', () => {
    expect(() => radialUnfold(slots.slice(1), cells, N, 1)).toThrow()
  })
  it('unfolds a subset around the full-grid centre', () => {
    const dark = cells.filter((c) => c.dark)
    const sub = radialUnfold(slots.slice(0, dark.length), dark, N, 1)
    expect(new Set(sub.map((p) => p.cell)).size).toBe(dark.length)
  })
})
