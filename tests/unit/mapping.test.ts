import { describe, expect, it } from 'vitest'
import { coneSlotCloud, qrCells, radialUnfold } from '../../src/mapping'
import { encodeQr, gridSize } from '../../src/qr'

const qr = encodeQr('https://github.com/gabrieljohnliew/seasonal-qr')
const cells = qrCells(qr)
const slots = coneSlotCloud(cells.length, 1)

describe('coneSlotCloud', () => {
  it('is deterministic per seed with sequential ids', () => {
    expect(coneSlotCloud(500, 7)).toEqual(coneSlotCloud(500, 7))
    expect(coneSlotCloud(500, 7)).not.toEqual(coneSlotCloud(500, 8))
    expect(coneSlotCloud(500, 7).map((s) => s.id)).toEqual([...Array(500).keys()])
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
  const pairs = radialUnfold(slots, cells, 1)
  it('is a bijection', () => {
    expect(new Set(pairs.map((p) => p.cell)).size).toBe(cells.length)
    expect(new Set(pairs.map((p) => p.slot.id)).size).toBe(slots.length)
  })
  it('gives finders delay 0 and the highest slots', () => {
    const fin = pairs.filter((p) => p.cell.finder)
    expect(fin.every((p) => p.delay === 0)).toBe(true)
    const minFinderY = Math.min(...fin.map((p) => p.slot.y))
    const others = pairs.filter((p) => !p.cell.finder)
    expect(others.every((p) => p.slot.y <= minFinderY)).toBe(true)
  })
  it('has delays in [0, 0.98) and is deterministic', () => {
    expect(pairs.every((p) => p.delay >= 0 && p.delay < 0.98)).toBe(true)
    expect(radialUnfold(slots, cells, 1)).toEqual(pairs)
  })
  it('rejects length mismatch', () => {
    expect(() => radialUnfold(slots.slice(1), cells, 1)).toThrow()
  })
})
