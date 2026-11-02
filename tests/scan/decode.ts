import jsQR from 'jsqr'
import { PNG } from 'pngjs'
import {
  BinaryBitmap,
  HybridBinarizer,
  QRCodeReader,
  RGBLuminanceSource,
} from '@zxing/library'
import sharp from 'sharp'

export interface DecodeResults {
  jsqr: string | null
  zxing: string | null
}

// Greyscale from RGBA, composited over white so transparent pixels read as light.
function toLuminance(data: Uint8Array, width: number, height: number): Uint8ClampedArray {
  const out = new Uint8ClampedArray(width * height)
  for (let i = 0, p = 0; i < out.length; i++, p += 4) {
    const a = data[p + 3] / 255
    const lum = 0.299 * data[p] + 0.587 * data[p + 1] + 0.114 * data[p + 2]
    out[i] = a * lum + (1 - a) * 255
  }
  return out
}

export function decodeAll(png: Buffer): DecodeResults {
  const { data, width, height } = PNG.sync.read(png)

  const jsqr = jsQR(new Uint8ClampedArray(data), width, height)?.data ?? null

  const reader = new QRCodeReader()
  let zxing: string | null = null
  try {
    const source = new RGBLuminanceSource(toLuminance(data, width, height), width, height)
    zxing = reader.decode(new BinaryBitmap(new HybridBinarizer(source))).getText()
  } catch {
    // ZXing throws NotFoundException (or Checksum/Format) when it cannot read a code: no result.
    zxing = null
  }

  return { jsqr, zxing }
}

// Approximates a phone camera: halve the resolution, soften by 1 px, then JPEG at quality 60.
export async function degrade(png: Buffer): Promise<Buffer> {
  const { width = 0, height = 0 } = await sharp(png).metadata()
  const jpeg = await sharp(png)
    .resize(Math.round(width / 2), Math.round(height / 2))
    .blur(1)
    .jpeg({ quality: 60 })
    .toBuffer()
  return sharp(jpeg).png().toBuffer()
}
