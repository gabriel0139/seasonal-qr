/// <reference types="node" />
import { expect, test } from 'vitest'
import QRCode from 'qrcode'
import { decodeAll, degrade } from '../scan/decode'

// Proves both decoders work independently of the renderer.
test('decodeAll reads a known QR PNG, direct and degraded', async () => {
  const text = 'https://example.com'
  const png = await QRCode.toBuffer(text, { errorCorrectionLevel: 'M', margin: 4, scale: 8 })
  expect(decodeAll(png)).toEqual({ jsqr: text, zxing: text })
  expect(decodeAll(await degrade(png))).toEqual({ jsqr: text, zxing: text })
})
