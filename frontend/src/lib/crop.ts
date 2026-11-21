import type { components } from './api.generated'

export type Crop = components['schemas']['Crop']
export const ASPECT_RATIOS = [
  { label: 'Freeform', value: 'free', ratio: null },
  { label: 'Original', value: 'original', ratio: null },
  { label: '1:1 · Square', value: '1:1', ratio: 1 },
  { label: '4:3 · Landscape', value: '4:3', ratio: 4 / 3 },
  { label: '3:2 · Photo', value: '3:2', ratio: 3 / 2 },
  { label: '16:9 · Widescreen', value: '16:9', ratio: 16 / 9 },
  { label: '3:4 · Portrait', value: '3:4', ratio: 3 / 4 },
  { label: '2:3 · Portrait', value: '2:3', ratio: 2 / 3 },
  { label: '4:5 · Social', value: '4:5', ratio: 4 / 5 },
  { label: '9:16 · Story', value: '9:16', ratio: 9 / 16 },
] as const

export const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, Math.round(value)))

export function fitCrop(width: number, height: number, ratio: number | null): Crop {
  const w = ratio ? Math.max(1, Math.min(width, Math.round(height * ratio))) : width
  const h = ratio ? Math.max(1, Math.min(height, Math.round(w / ratio))) : height
  return { x: Math.floor((width - w) / 2), y: Math.floor((height - h) / 2), width: w, height: h }
}

export function moveCrop(crop: Crop, x: number, y: number, width: number, height: number): Crop {
  return { ...crop, x: clamp(x, 0, width - crop.width), y: clamp(y, 0, height - crop.height) }
}

export function resizeCrop(crop: Crop, dx: number, dy: number, corner: string, width: number, height: number, ratio: number | null): Crop {
  const left = corner.includes('w'), top = corner.includes('n')
  const anchorX = left ? crop.x + crop.width : crop.x
  const anchorY = top ? crop.y + crop.height : crop.y
  const maxW = left ? anchorX : width - anchorX
  const maxH = top ? anchorY : height - anchorY
  let w = clamp(crop.width + (left ? -dx : dx), 1, maxW)
  let h = clamp(crop.height + (top ? -dy : dy), 1, maxH)
  if (ratio) {
    const proposed = Math.abs(dx) >= Math.abs(dy) ? w : h * ratio
    w = clamp(proposed, 1, Math.max(1, Math.min(maxW, maxH * ratio)))
    h = clamp(w / ratio, 1, maxH)
  }
  return { x: left ? anchorX - w : anchorX, y: top ? anchorY - h : anchorY, width: w, height: h }
}
