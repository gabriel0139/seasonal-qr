import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { describe, expect, test } from 'vitest'

// The manifest is the licence and credit record for every shipped asset (plan §17).
interface Entry {
  path?: string
  slots?: string
  licence: string
  author: string
}

const manifest: Entry[] = JSON.parse(readFileSync('assets-manifest.json', 'utf8'))
const listed = (dir: string) => readdirSync(dir).filter((f) => !f.startsWith('.'))
const models = listed('public/models').map((f) => `public/models/${f}`)
const trees = listed('public/trees').map((f) => `public/trees/${f}`)
const paths = new Set(manifest.map((e) => e.path).filter(Boolean))
const slotFiles = new Set(manifest.map((e) => e.slots).filter(Boolean))

describe('assets manifest', () => {
  test.each(models)('%s has a manifest entry', (f) => {
    expect(paths.has(f)).toBe(true)
  })

  test.each(trees)('%s has a manifest entry (as slots)', (f) => {
    expect(slotFiles.has(f)).toBe(true)
  })

  test.each(manifest.flatMap((e) => [e.path, e.slots].filter((p): p is string => !!p)))(
    '%s exists',
    (f) => {
      expect(existsSync(f)).toBe(true)
    },
  )

  test.each(manifest.map((e) => [e.path ?? e.slots, e] as const))('%s has a licence and author', (_, e) => {
    expect(['CC0-1.0', 'CC-BY-4.0']).toContain(e.licence)
    expect(e.author.trim()).not.toBe('')
  })
})
