// Pure types for the QR engine. No rendering imports allowed in src/qr.

/** Modules per side of the quiet zone (QR spec minimum). */
export const QUIET_ZONE = 4
/** Input is capped at this version at EC level M (plan §3.1). */
export const MAX_VERSION = 10
export const EC_LEVEL = 'M' as const

export interface QrResult {
  /** QR version 1..MAX_VERSION */
  version: number
  /** Modules per side, n = 4 * version + 17 (no quiet zone) */
  size: number
  /** Row-major n*n, 1 = dark module, 0 = light */
  modules: Uint8Array
  text: string
}

export type DensityLabel = 'Short' | 'Medium' | 'Dense' | 'Too long'

export interface Density {
  bytes: number
  /** null when the payload exceeds MAX_VERSION at EC_LEVEL */
  version: number | null
  label: DensityLabel
  /** (size + 2 * QUIET_ZONE)^2, or null when too long */
  tiles: number | null
}
