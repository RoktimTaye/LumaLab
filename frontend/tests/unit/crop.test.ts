import { describe, expect, it } from 'vitest'
import { ASPECT_RATIOS, fitCrop, moveCrop, resizeCrop } from '../../src/lib/crop'

describe('crop geometry', () => {
  it('fits every preset inside landscape, portrait and tiny photographs', () => {
    for (const [width, height] of [[4032, 3024], [600, 1200], [1, 1], [10000, 1], [1, 10000]]) {
      for (const { ratio } of ASPECT_RATIOS) {
        const crop = fitCrop(width, height, ratio)
        expect(crop.x).toBeGreaterThanOrEqual(0)
        expect(crop.y).toBeGreaterThanOrEqual(0)
        expect(crop.width).toBeGreaterThan(0)
        expect(crop.height).toBeGreaterThan(0)
        expect(crop.x + crop.width).toBeLessThanOrEqual(width)
        expect(crop.y + crop.height).toBeLessThanOrEqual(height)
      }
    }
    expect(fitCrop(1200, 800, 1)).toEqual({ x: 200, y: 0, width: 800, height: 800 })
    expect(fitCrop(1200, 800, null)).toEqual({ x: 0, y: 0, width: 1200, height: 800 })
  })
  it('clamps movement and resizes from all corners without crossing the image', () => {
    const crop = { x: 100, y: 100, width: 400, height: 300 }
    expect(moveCrop(crop, -1000, 1000, 800, 600)).toEqual({ ...crop, x: 0, y: 300 })
    for (const corner of ['nw', 'ne', 'sw', 'se']) {
      for (const delta of [-10000, -1, 0, 10, 10000]) {
        for (const ratio of [null, 1, 16 / 9, 9 / 16]) {
          const next = resizeCrop(crop, delta, delta / 2, corner, 800, 600, ratio)
          expect(next.x).toBeGreaterThanOrEqual(0)
          expect(next.y).toBeGreaterThanOrEqual(0)
          expect(next.width).toBeGreaterThan(0)
          expect(next.height).toBeGreaterThan(0)
          expect(next.x + next.width).toBeLessThanOrEqual(800)
          expect(next.y + next.height).toBeLessThanOrEqual(600)
          if (ratio) expect(Math.abs(next.height - next.width / ratio)).toBeLessThanOrEqual(1)
        }
      }
    }
  })
})
