// Captures the reveal animation as a grid of frames so the motion can be judged from one PNG.
// Usage: npm run reveal:strip -- [--text=<payload>] [--frames=12] [--out=reveal-strip.png] [--size=600]
import { spawn } from 'node:child_process'
import { writeFile } from 'node:fs/promises'
import { chromium } from '@playwright/test'
import sharp from 'sharp'

const PORT = 5173
const BASE = `http://localhost:${PORT}`
const root = new URL('..', import.meta.url).pathname

const args = Object.fromEntries(
  process.argv.slice(2).map((a) => {
    const m = a.match(/^--([^=]+)(?:=(.*))?$/)
    if (!m) throw new Error(`bad argument: ${a}`)
    return [m[1], m[2] ?? '']
  }),
)
const text = args.text ?? 'https://google.com'
const frames = Number(args.frames ?? 12)
const out = args.out ?? 'reveal-strip.png'
const size = Number(args.size ?? 600)
if (!Number.isInteger(frames) || frames < 1) throw new Error('--frames must be a positive integer')
if (!Number.isInteger(size) || size < 1) throw new Error('--size must be a positive integer')

async function responds() {
  try {
    await fetch(BASE)
    return true
  } catch {
    return false
  }
}

async function startServer() {
  if (await responds()) return { child: null }
  const child = spawn('npx', ['vite', '--port', String(PORT), '--strictPort'], {
    cwd: root,
    stdio: 'ignore',
    detached: true, // own process group so the whole npx -> vite tree can be killed
  })
  let exited = false
  child.on('exit', () => (exited = true))
  const deadline = Date.now() + 60_000
  while (!(await responds())) {
    if (exited) throw new Error('vite dev server exited before becoming ready')
    if (Date.now() > deadline) throw new Error(`vite dev server did not respond on ${BASE} within 60s`)
    await new Promise((r) => setTimeout(r, 300))
  }
  return { child }
}

function stopServer(child) {
  if (!child || child.exitCode !== null) return
  try {
    process.kill(-child.pid, 'SIGTERM')
  } catch {
    child.kill('SIGTERM')
  }
}

async function captureFrames() {
  const browser = await chromium.launch({
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
  })
  try {
    const page = await browser.newPage({ viewport: { width: size, height: size }, deviceScaleFactor: 1 })
    const pageErrors = []
    page.on('pageerror', (e) => pageErrors.push(e.message))
    await page.goto(`${BASE}/?text=${encodeURIComponent(text)}`)
    await page.waitForSelector('canvas')
    await page.waitForTimeout(1500) // GLB load

    // Rounded to the slider's 0.001 step; fill() rejects values with more decimals.
    const progresses = frames === 1 ? [0] : Array.from({ length: frames }, (_, i) => Number((i / (frames - 1)).toFixed(3)))
    const buffers = []
    for (const p of progresses) {
      await page.locator('input[type=range]').fill(String(p))
      await page.waitForTimeout(400)
      buffers.push(await page.locator('canvas').screenshot())
    }
    if (pageErrors.length) throw new Error(`page errors: ${pageErrors.join(' | ')}`)
    return buffers
  } finally {
    await browser.close()
  }
}

async function compose(buffers) {
  const GUTTER = 8
  const metas = await Promise.all(buffers.map((b) => sharp(b).metadata()))
  const cellW = Math.max(...metas.map((m) => m.width))
  const cellH = Math.max(...metas.map((m) => m.height))
  const cols = Math.min(4, buffers.length)
  const rows = Math.ceil(buffers.length / cols)
  const width = cols * cellW + (cols - 1) * GUTTER
  const height = rows * cellH + (rows - 1) * GUTTER
  const composites = buffers.map((input, i) => ({
    input,
    left: (i % cols) * (cellW + GUTTER),
    top: Math.floor(i / cols) * (cellH + GUTTER),
  }))
  return sharp({ create: { width, height, channels: 3, background: '#ffffff' } })
    .composite(composites)
    .png()
    .toBuffer()
}

const { child } = await startServer()
try {
  const buffers = await captureFrames()
  await writeFile(out, await compose(buffers))
  console.log(out)
} catch (err) {
  console.error(`reveal:strip failed: ${err.message}`)
  process.exitCode = 1
} finally {
  stopServer(child)
}
