import { test, expect } from '@playwright/test'
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { decodeAll, degrade } from './decode'

const SHOT_DIR = join(dirname(fileURLToPath(import.meta.url)), '__screenshots__')

const PAYLOADS = [
  { name: 'short-url', text: 'https://example.com' },
  // 202 bytes: just under the v10/M byte-mode cap of 213.
  { name: 'long-url', text: 'https://example.com/p/' + 'abcdefghij'.repeat(18) },
  { name: 'non-latin', text: 'こんにちは世界、桜の季節です' },
  { name: 'emoji', text: 'Seasonal QR 🌸🌸🌸' },
  { name: 'minimal', text: 'HELLO' },
]

for (const { name, text } of PAYLOADS) {
  test(name, async ({ page }, testInfo) => {
    await page.goto('/?t=end&text=' + encodeURIComponent(text))
    await page.waitForSelector('body[data-ready="true"]', { timeout: 30000 })
    const png = await page.locator('canvas').screenshot()

    if (process.env.UPDATE_SCREENSHOTS) {
      mkdirSync(SHOT_DIR, { recursive: true })
      writeFileSync(join(SHOT_DIR, `${name}.png`), png)
    }

    const degraded = await degrade(png)
    const direct = decodeAll(png)
    const blurred = decodeAll(degraded)
    const expected = { jsqr: text, zxing: text }

    if (JSON.stringify(direct) !== JSON.stringify(expected) || JSON.stringify(blurred) !== JSON.stringify(expected)) {
      await testInfo.attach(`${name}.png`, { body: png, contentType: 'image/png' })
      await testInfo.attach(`${name}-degraded.png`, { body: degraded, contentType: 'image/png' })
    }

    expect(direct, 'direct render').toEqual(expected)
    expect(blurred, 'degraded render').toEqual(expected)
  })
}
