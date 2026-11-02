// Pure types for tree → QR mapping. No rendering imports allowed in src/mapping.

/** One tile position in the tree state. Tree space: y up, trunk base at origin, units ≈ one tile. */
export interface Slot {
  id: number
  x: number
  y: number
  z: number
  /** index into the season palette (0 = trunk, 1.. = foliage shades) */
  paletteIndex: number
}

/** One cell of the full grid including the quiet zone. col/row are 0..gridSize-1. */
export interface Cell {
  col: number
  row: number
  dark: boolean
  /** true for the 3 × 7×7 finder patterns (they land first) */
  finder: boolean
}

export interface TilePair {
  slot: Slot
  cell: Cell
  /** normalised start delay in [0, 1): a tile animates over local t = (progress - delay) / (1 - delay) */
  delay: number
}
