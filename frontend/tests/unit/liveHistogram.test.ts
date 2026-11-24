import { describe, expect, it } from 'vitest'
import { histogramData, livePixels } from '../../src/lib/liveHistogram'
import { NEUTRAL } from '../../src/lib/editor'
import { identityCurves } from '../../src/lib/curves'

describe('live histogram',()=>{
  const source=new Uint8ClampedArray([64,64,64,255,128,128,128,255])
  it('responds to exposure from cached source pixels without a server image',()=>{
    const curves=identityCurves()
    const original=source.slice()
    const neutral=histogramData(livePixels(source,2,1,NEUTRAL,curves))
    const bright=histogramData(livePixels(source,2,1,{...NEUTRAL,exposure:1},curves))
    expect(neutral.bins[64]).toBe(1)
    expect(bright.bins[128]).toBe(1)
    expect(bright.bins[255]).toBe(1)
    expect(bright.light).toBe(50)
    expect(source).toEqual(original)
  })
  it('reacts to RGB curve point changes and returns to neutral on reset',()=>{
    const curves=identityCurves()
    const before=livePixels(source,2,1,NEUTRAL,curves)
    curves.rgb.points=[{x:0,y:0},{x:128,y:200},{x:255,y:255}]
    const after=livePixels(source,2,1,NEUTRAL,curves)
    expect(after[4]).toBeGreaterThan(before[4])
    expect(livePixels(source,2,1,NEUTRAL,identityCurves())).toEqual(before)
  })
  it('changes colour channel counts with saturation and tint',()=>{
    const colourful=new Uint8ClampedArray([180,90,20,255])
    const mono=livePixels(colourful,1,1,{...NEUTRAL,saturation:0},identityCurves())
    expect(mono[0]).toBe(mono[1]);expect(mono[1]).toBe(mono[2])
    const tinted=livePixels(source,2,1,{...NEUTRAL,tint:50},identityCurves())
    expect(tinted[0]).toBeGreaterThan(tinted[1])
  })
})
