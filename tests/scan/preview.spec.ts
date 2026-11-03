import { test, expect } from '@playwright/test'
import { existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { seasons } from '../../src/seasons'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '../..')
const TEXT = encodeURIComponent('https://example.com')

// Plan §8.1: reviewers see each tree and its QR in the CI report without cloning.
for (const season of Object.values(seasons)) {
  test(`preview-${season.id}`, async ({ page }, testInfo) => {
    test.skip(!existsSync(join(ROOT, 'public/models', `${season.id}.glb`)), `public/models/${season.id}.glb is missing`)
    await page.goto(`/?season=${season.id}&text=${TEXT}`)
    await page.waitForSelector('canvas', { timeout: 30000 })
    await page.waitForTimeout(1500)
    const tree = await page.locator('canvas').screenshot()
    await page.goto(`/?t=end&season=${season.id}&text=${TEXT}`)
    await page.waitForSelector('body[data-ready="true"]', { timeout: 30000 })
    const qr = await page.locator('canvas').screenshot()
    await testInfo.attach(`${season.id}-tree.png`, { body: tree, contentType: 'image/png' })
    await testInfo.attach(`${season.id}-qr.png`, { body: qr, contentType: 'image/png' })
    expect(tree.length).toBeGreaterThan(0)
    expect(qr.length).toBeGreaterThan(0)
  })
}
