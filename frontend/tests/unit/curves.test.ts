import { describe, expect, it } from 'vitest'
import { curveValue, curvesAreNeutral, identityCurves } from '../../src/lib/curves'

describe('point curves', () => {
  it('starts neutral and creates independent channel points', () => {
    const curves = identityCurves()
    expect(curvesAreNeutral(curves)).toBe(true)
    curves.red.points[0].y = 20
    expect(curvesAreNeutral(curves)).toBe(false)
    expect(curves.rgb.points[0].y).toBe(0)
    expect(identityCurves().red.points[0].y).toBe(0)
  })
  it('interpolates all anchors and stays inside segment bounds', () => {
    const points = [{x:0,y:220},{x:64,y:20},{x:128,y:240},{x:255,y:0}]
    for (const p of points) expect(curveValue(points,p.x)).toBeCloseTo(p.y)
    for (let i=0;i<points.length-1;i++) {
      for (let x=points[i].x;x<=points[i+1].x;x++) {
        const y=curveValue(points,x)
        expect(y).toBeGreaterThanOrEqual(Math.min(points[i].y,points[i+1].y)-1e-10)
        expect(y).toBeLessThanOrEqual(Math.max(points[i].y,points[i+1].y)+1e-10)
      }
    }
  })
  it('keeps neutral values exact at every intensity', () => {
    for (let x=0;x<256;x++) expect(curveValue(identityCurves().rgb.points,x)).toBeCloseTo(x)
  })
})
