import { QUIET_ZONE, type QrResult } from '../qr/types'
import type { Cell, Slot, TilePair } from './types'

export * from './types'

/** mulberry32: floats in [0,1) */
export function seededRandom(seed: number): () => number {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/** Placeholder cone tree: thin trunk plus uniformly filled cone canopy, in shuffled order. */
export function coneSlotCloud(count: number, seed: number): Slot[] {
  const rand = seededRandom(seed)
  const height = Math.cbrt(count) * 3
  const baseY = height * 0.2
  const baseR = height * 0.35
  const trunkCount = Math.round(count * 0.08)
  const slots: Slot[] = []
  for (let i = 0; i < count; i++) {
    if (i < trunkCount) {
      const a = rand() * 2 * Math.PI
      const r = Math.sqrt(rand()) * 0.8
      slots.push({ id: 0, x: r * Math.cos(a), y: rand() * height * 0.25, z: r * Math.sin(a), paletteIndex: 0 })
    } else {
      const f = 1 - Math.cbrt(rand()) // uniform over cone volume (area grows with (1-f)^2)
      const r = baseR * (1 - f) * Math.sqrt(rand())
      const a = rand() * 2 * Math.PI
      slots.push({ id: 0, x: r * Math.cos(a), y: baseY + f * (height - baseY), z: r * Math.sin(a), paletteIndex: rand() < 0.5 ? 1 : 2 })
    }
  }
  for (let i = count - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1))
    ;[slots[i], slots[j]] = [slots[j], slots[i]]
  }
  return slots.map((s, id) => ({ ...s, id }))
}

export function qrCells(qr: QrResult): Cell[] {
  const n = qr.size + 2 * QUIET_ZONE
  const lo = QUIET_ZONE
  const hi = QUIET_ZONE + qr.size - 7
  const inFinder = (c: number, r: number) =>
    [[lo, lo], [hi, lo], [lo, hi]].some(([c0, r0]) => c >= c0 && c < c0 + 7 && r >= r0 && r < r0 + 7)
  const cells: Cell[] = []
  for (let row = 0; row < n; row++) {
    for (let col = 0; col < n; col++) {
      const mc = col - QUIET_ZONE
      const mr = row - QUIET_ZONE
      const inside = mc >= 0 && mr >= 0 && mc < qr.size && mr < qr.size
      cells.push({ col, row, dark: inside && qr.modules[mr * qr.size + mc] === 1, finder: inFinder(col, row) })
    }
  }
  return cells
}

// Fixed chunk: a "ring" of cells grows with radius, but a constant 64 keeps azimuth bands narrow
// enough to stay local while wide enough to pair smoothly; it is also simple and deterministic.
const CHUNK = 64

export function radialUnfold(slots: Slot[], cells: Cell[], seed: number): TilePair[] {
  if (slots.length !== cells.length) throw new Error(`slots (${slots.length}) and cells (${cells.length}) differ`)
  const rand = seededRandom(seed)
  const n = Math.sqrt(cells.length)
  const c = (n - 1) / 2
  const radius = (k: Cell) => Math.hypot(k.col - c, k.row - c)
  const angle = (k: Cell) => Math.atan2(k.row - c, k.col - c)
  const azimuth = (s: Slot) => Math.atan2(s.z, s.x)
  const rMax = Math.max(...cells.map(radius))

  const byHeight = [...slots].sort((a, b) => b.y - a.y || a.id - b.id)
  const finderCells = cells.filter((k) => k.finder).sort((a, b) => angle(a) - angle(b))
  const finderSlots = byHeight.slice(0, finderCells.length).sort((a, b) => azimuth(a) - azimuth(b))
  const pairs: TilePair[] = finderCells.map((cell, i) => ({ slot: finderSlots[i], cell, delay: 0 }))

  const s = byHeight.slice(finderCells.length).reverse()
  const g = cells.filter((k) => !k.finder).sort((a, b) => radius(a) - radius(b))
  for (let i = 0; i < g.length; i += CHUNK) {
    const sChunk = s.slice(i, i + CHUNK).sort((a, b) => azimuth(a) - azimuth(b))
    const gChunk = g.slice(i, i + CHUNK).sort((a, b) => angle(a) - angle(b))
    gChunk.forEach((cell, j) => {
      const delay = 0.15 + 0.75 * (radius(cell) / rMax) + rand() * 0.05
      pairs.push({ slot: sChunk[j], cell, delay: Math.min(delay, 0.979) })
    })
  }
  return pairs
}
