import { describe, expect, it } from 'vitest'
import { inspectFile, NEUTRAL, PRESETS } from '../../src/lib/editor'

describe('frontend upload checks', () => {
  it('detects JPEG bytes instead of trusting a filename', () => {
    expect(inspectFile(new Uint8Array([255,216,255]), 'picture.jpeg', 3)).toBe('JPEG')
    expect(() => inspectFile(new Uint8Array([255,216,255]), 'picture.png', 3)).toThrow('matching file extension')
    expect(() => inspectFile(new Uint8Array([1,2,3]), 'picture.jpg', 3)).toThrow('Choose a still')
  })
  it('rejects files above the exact decimal byte limit', () => {
    expect(() => inspectFile(new Uint8Array([255,216,255]), 'picture.jpg', 10_000_001)).toThrow('10 MB')
    expect(inspectFile(new Uint8Array([255,216,255]), 'picture.jpg', 10_000_000)).toBe('JPEG')
  })
  it('rejects APNG animation chunks', () => {
    const bytes = new Uint8Array([137,80,78,71,13,10,26,10,0,0,0,0,97,99,84,76,0,0,0,0])
    expect(() => inspectFile(bytes, 'animated.png', bytes.length)).toThrow('Animated images')
  })
  it('rejects WebP animation chunks', () => {
    const bytes = new Uint8Array([82,73,70,70,12,0,0,0,87,69,66,80,65,78,73,77,0,0,0,0])
    expect(() => inspectFile(bytes, 'animated.webp', bytes.length)).toThrow('Animated images')
  })
  it('presets provide complete values and monochrome remains neutral in warmth', () => {
    for (const preset of PRESETS) expect(Object.keys(preset.values).sort()).toEqual(Object.keys(NEUTRAL).sort())
    expect(PRESETS.find(p => p.name === 'Monochrome')?.values).toMatchObject({ saturation: 0, warmth: 0 })
    expect(PRESETS[0].values).toEqual(NEUTRAL)
  })
})
