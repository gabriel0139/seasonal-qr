import QRCode from 'qrcode'
import { EC_LEVEL, MAX_VERSION, QUIET_ZONE, type Density, type QrResult } from './types'

export * from './types'

export function encodeQr(text: string): QrResult {
  const r = QRCode.create(text, { errorCorrectionLevel: EC_LEVEL })
  if (r.version > MAX_VERSION) throw new RangeError(`QR version ${r.version} exceeds max ${MAX_VERSION}`)
  return { version: r.version, size: r.modules.size, modules: Uint8Array.from(r.modules.data), text }
}

export const byteLength = (text: string): number => new TextEncoder().encode(text).length

export const gridSize = (version: number): number => 4 * version + 17 + 2 * QUIET_ZONE

export const tileCount = (version: number): number => gridSize(version) ** 2

export function density(text: string): Density {
  const bytes = byteLength(text)
  if (bytes === 0) return { bytes, version: null, label: 'Short', tiles: null } // qrcode throws on empty input
  try {
    const { version } = encodeQr(text)
    const label = version <= 3 ? 'Short' : version <= 6 ? 'Medium' : 'Dense'
    return { bytes, version, label, tiles: tileCount(version) }
  } catch (e) {
    if (e instanceof RangeError) return { bytes, version: null, label: 'Too long', tiles: null }
    throw e
  }
}
