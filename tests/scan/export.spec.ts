import { test, expect } from '@playwright/test'
import sharp from 'sharp'
import { decodeAll } from './decode'

const PAYLOADS = ['https://example.com', 'こんにちは世界、桜の季節です']

for (const text of PAYLOADS) {
  test(`exported files scan: ${text}`, async ({ page }) => {
    await page.goto('/?season=sakura&text=' + encodeURIComponent(text))
    await page.waitForSelector('a[download="seasonal-qr.svg"]', { state: 'attached' })
    const href = (name: string) => page.locator(`a[download="${name}"]`).getAttribute('href')
    const expected = { jsqr: text, zxing: text }

    const svg = decodeURIComponent((await href('seasonal-qr.svg'))!.replace('data:image/svg+xml,', ''))
    const fromSvg = await sharp(Buffer.from(svg), { density: 300 }).resize(600).flatten({ background: '#fff' }).png().toBuffer()
    expect(decodeAll(fromSvg), 'svg export').toEqual(expected)

    const png = Buffer.from((await href('seasonal-qr.png'))!.replace('data:image/png;base64,', ''), 'base64')
    expect(decodeAll(png), 'png export').toEqual(expected)
  })
}
