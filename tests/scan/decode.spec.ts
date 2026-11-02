import { test, expect } from '@playwright/test'
import { existsSync, mkdirSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { seasons } from '../../src/seasons'
import { decodeAll, degrade } from './decode'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '../..')
const SHOT_DIR = join(dirname(fileURLToPath(import.meta.url)), '__screenshots__')

const PAYLOADS = [
  { name: 'short-url', text: 'https://example.com' },
  // 202 bytes: just under the v10/M byte-mode cap of 213.
  { name: 'long-url', text: 'https://example.com/p/' + 'abcdefghij'.repeat(18) },
  { name: 'non-latin', text: 'こんにちは世界、桜の季節です' },
  { name: 'emoji', text: 'Seasonal QR 🌸🌸🌸' },
  { name: 'minimal', text: 'HELLO' },
]

for (const season of Object.values(seasons)) {
  for (const { name, text } of PAYLOADS) {
    const file = `${name}-${season.id}`
    test(file, async ({ page }, testInfo) => {
      // The matrix grows by itself when a season's assets land.
      test.skip(!existsSync(join(ROOT, 'public/models', `${season.id}.glb`)), `public/models/${season.id}.glb is missing`)
      await page.goto(`/?t=end&season=${season.id}&text=` + encodeURIComponent(text))
      await page.waitForSelector('body[data-ready="true"]', { timeout: 30000 })
      const png = await page.locator('canvas').screenshot()

      if (process.env.UPDATE_SCREENSHOTS) {
        mkdirSync(SHOT_DIR, { recursive: true })
        writeFileSync(join(SHOT_DIR, `${file}.png`), png)
      }

      const degraded = await degrade(png)
      const direct = decodeAll(png)
      const blurred = decodeAll(degraded)
      const expected = { jsqr: text, zxing: text }

      if (JSON.stringify(direct) !== JSON.stringify(expected) || JSON.stringify(blurred) !== JSON.stringify(expected)) {
        await testInfo.attach(`${file}.png`, { body: png, contentType: 'image/png' })
        await testInfo.attach(`${file}-degraded.png`, { body: degraded, contentType: 'image/png' })
      }

      expect(direct, 'direct render').toEqual(expected)
      expect(blurred, 'degraded render').toEqual(expected)
    })
  }
}
