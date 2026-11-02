import { describe, expect, it } from 'vitest'
import { byteLength, density, encodeQr, gridSize, tileCount } from '../../src/qr'

describe('qr', () => {
  it('encodes a short URL at version 2-4', () => {
    const qr = encodeQr('https://github.com/gabrieljohnliew/seasonal-qr')
    expect(qr.version).toBeGreaterThanOrEqual(2)
    expect(qr.version).toBeLessThanOrEqual(4)
    expect(qr.size).toBe(4 * qr.version + 17)
    expect(qr.modules.length).toBe(qr.size ** 2)
  })
  it('throws RangeError past the cap', () => {
    expect(() => encodeQr('a'.repeat(300))).toThrow(RangeError)
  })
  it('counts UTF-8 bytes and labels density', () => {
    expect(byteLength('🌸')).toBe(4)
    expect(density('hi')).toMatchObject({ bytes: 2, label: 'Short', version: 1 })
    expect(density('a'.repeat(60)).label).toBe('Medium')
    expect(density('a'.repeat(150)).label).toBe('Dense')
    expect(density('a'.repeat(300))).toMatchObject({ label: 'Too long', version: null, tiles: null })
    expect(density('')).toMatchObject({ bytes: 0, version: null, tiles: null })
  })
  it('computes grid and tile counts', () => {
    expect(gridSize(10)).toBe(65)
    expect(tileCount(10)).toBe(4225)
  })
})
