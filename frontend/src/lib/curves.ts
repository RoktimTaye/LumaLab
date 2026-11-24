import type { RGBCurves } from './api'

export type CurveChannel = keyof RGBCurves
export type CurvePoint = { x: number; y: number }
export const CHANNELS: CurveChannel[] = ['rgb', 'red', 'green', 'blue']
export function identityCurves(): RGBCurves {
  const curve = () => ({ points: [{ x: 0, y: 0 }, { x: 255, y: 255 }] })
  return { rgb: curve(), red: curve(), green: curve(), blue: curve() }
}
export function curvesAreNeutral(curves: RGBCurves): boolean {
  return CHANNELS.every(channel => curves[channel].points.every(p => p.x === p.y))
}

// Same shape-preserving cubic interpolation as the image renderer.
export function curveValue(points: CurvePoint[], value: number): number {
  const h = points.slice(1).map((p, i) => p.x - points[i].x)
  const d = points.slice(1).map((p, i) => (p.y - points[i].y) / h[i])
  const slopes = points.map((_, i) => {
    if (i === 0) return d[0]
    if (i === points.length - 1) return d[d.length - 1]
    if (d[i - 1] * d[i] <= 0) return 0
    const w1 = 2 * h[i] + h[i - 1], w2 = h[i] + 2 * h[i - 1]
    return (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
  })
  let i = 0
  while (i < points.length - 2 && value >= points[i + 1].x) i++
  const t = (value - points[i].x) / h[i]
  return Math.max(0, Math.min(255,
    (2*t**3 - 3*t**2 + 1)*points[i].y + (t**3 - 2*t**2 + t)*h[i]*slopes[i]
    + (-2*t**3 + 3*t**2)*points[i+1].y + (t**3 - t**2)*h[i]*slopes[i+1]))
}
