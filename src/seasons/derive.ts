// A season's colours come from the Blender scene's palette (the slot JSON); everything the decoder needs is derived here.
export interface Season {
  /** URL id and file stem */
  id: string
  /** UI label */
  name: string
  /** start colours of the tiles in the tree, indexed by Slot.paletteIndex:
   * 0 trunk, 1–3 canopy shades, 4 lawn, 5 wood, 6 stone, 7 pond water */
  tree: string[]
  /** landed colour of dark modules by slot class; one luma for all, because decoders threshold locally */
  finalDark: string[]
  /** landed colour of light modules and the quiet zone */
  finalLight: string
  /** world units across the base top; the landed QR always spans this */
  baseSize: number
  /** slot classes whose `tree` colours the falling particles use */
  petals: number[]
}

export type SeasonJson = { palette: string[]; baseSize: number }
export type Overrides = Partial<Pick<Season, 'finalDark' | 'finalLight' | 'petals'>>

export const DARK_LUMA = 56
export const LIGHT_LUMA = 232

export const hexToRgb = (hex: string): number[] => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))

export const luma = (hex: string) => hexToRgb(hex).reduce((s, v, i) => s + v * [0.299, 0.587, 0.114][i], 0)

function hslToHex(h: number, s: number, l: number): string {
  const f = (n: number) => {
    const k = (n + h * 12) % 12
    return l - s * Math.min(l, 1 - l) * Math.max(-1, Math.min(k - 3, 9 - k, 1))
  }
  return '#' + [f(0), f(8), f(4)].map((v) => Math.round(v * 255).toString(16).padStart(2, '0')).join('')
}

/** `hex` with its hue kept, saturation clamped to [minSat, maxSat] and lightness solved so the luma hits `target`. */
export function withLuma(hex: string, target: number, minSat = 0, maxSat = 1): string {
  const [r, g, b] = hexToRgb(hex).map((v) => v / 255)
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  const d = max - min
  const l0 = (max + min) / 2
  let h = 0
  if (d) {
    h = max === r ? ((g - b) / d + 6) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4
    h /= 6
  }
  const s0 = d ? d / (1 - Math.abs(2 * l0 - 1)) : 0
  // shortcut: greys keep their saturation (no hue to boost), so a grey stone stays grey
  const s = s0 < 0.08 ? s0 : Math.min(maxSat, Math.max(minSat, s0))
  let lo = 0
  let hi = 1
  for (let i = 0; i < 20; i++) {
    const mid = (lo + hi) / 2
    if (luma(hslToHex(h, s, mid)) < target) lo = mid
    else hi = mid
  }
  return hslToHex(h, s, (lo + hi) / 2)
}

export function deriveSeason(id: string, name: string, json: SeasonJson, overrides: Overrides = {}): Season {
  return {
    id,
    name,
    tree: json.palette,
    finalDark: json.palette.map((c) => withLuma(c, DARK_LUMA, 0.55)),
    finalLight: withLuma(json.palette[4], LIGHT_LUMA, 0, 0.45),
    baseSize: json.baseSize,
    petals: [1, 2, 3],
    ...overrides,
  }
}
