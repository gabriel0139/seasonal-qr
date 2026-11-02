// page.evaluate bodies run in the browser
/// <reference lib="dom" />
import { test, expect } from '@playwright/test'
import { readFileSync } from 'node:fs'
import { decodeAll } from './decode'

const TEXT = 'https://example.com'

test('exported video ends on a scannable frame', async ({ page }, testInfo) => {
  test.setTimeout(120_000)
  await page.goto('/?season=sakura&text=' + encodeURIComponent(TEXT))
  await page.locator('canvas').waitFor()
  await page.waitForTimeout(1500) // let the GLB land

  // Live canvas size and reveal progress must come back exactly as they were.
  const state = () => page.evaluate(() => [document.querySelector('canvas')!.width, document.querySelector<HTMLInputElement>('input[type=range]')!.value])
  const before = await state()
  const [download] = await Promise.all([page.waitForEvent('download', { timeout: 110_000 }), page.getByRole('button', { name: 'Export video' }).click()])
  const name = download.suggestedFilename()
  expect(name).toMatch(/^seasonal-qr\.(mp4|webm)$/)
  const file = testInfo.outputPath(name)
  await download.saveAs(file)
  await expect(page.getByRole('button', { name: 'Export video' })).toBeVisible()
  expect(await state()).toEqual(before)

  // Decode the last frame in a fresh page: seek near the end, draw it to a canvas, read it back as PNG.
  const src = `data:video/${name.split('.')[1]};base64,${readFileSync(file).toString('base64')}`
  await page.setContent('<video muted></video><canvas></canvas>')
  const png = await page.evaluate(async (src) => {
    const video = document.querySelector('video')!
    video.src = src
    await new Promise((r) => (video.onloadedmetadata = r))
    video.currentTime = video.duration - 0.05
    await new Promise((r) => (video.onseeked = r))
    const canvas = document.querySelector('canvas')!
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext('2d')!.drawImage(video, 0, 0)
    return canvas.toDataURL('image/png').split(',')[1]
  }, src)

  const frame = Buffer.from(png, 'base64')
  const result = decodeAll(frame)
  if (result.jsqr !== TEXT || result.zxing !== TEXT) await testInfo.attach('last-frame.png', { body: frame, contentType: 'image/png' })
  expect(result).toEqual({ jsqr: TEXT, zxing: TEXT })
})
