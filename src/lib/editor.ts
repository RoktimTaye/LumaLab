export type Adjustments = { brightness: number; contrast: number; saturation: number; warmth: number; sharpness: number; vignette: number }
export type AdjustmentKey = keyof Adjustments
export type Preset = { name: string; description: string; values: Adjustments }
export const NEUTRAL: Adjustments = { brightness: 100, contrast: 100, saturation: 100, warmth: 0, sharpness: 0, vignette: 0 }
export const PRESETS: Preset[] = [
  { name: 'Original', description: 'Just as you captured it', values: { ...NEUTRAL } },
  { name: 'Cinematic', description: 'Cool tones. Quiet drama.', values: { brightness: 98, contrast: 120, saturation: 78, warmth: -12, sharpness: 12, vignette: 22 } },
  { name: 'Golden Hour', description: 'A little more sunshine', values: { brightness: 110, contrast: 94, saturation: 112, warmth: 22, sharpness: 5, vignette: 8 } },
  { name: 'Monochrome', description: 'A story in light and shadow', values: { brightness: 102, contrast: 125, saturation: 0, warmth: 0, sharpness: 18, vignette: 16 } },
  { name: 'Vivid', description: 'Colour with confidence', values: { brightness: 103, contrast: 110, saturation: 140, warmth: 2, sharpness: 30, vignette: 0 } },
]
export const CONTROL_GROUPS: { name: string; color: string; controls: { key: AdjustmentKey; label: string; min: number; max: number }[] }[] = [
  { name: 'Light', color: 'var(--red)', controls: [{ key: 'brightness', label: 'Brightness', min: 0, max: 200 }, { key: 'contrast', label: 'Contrast', min: 0, max: 200 }] },
  { name: 'Colour', color: 'var(--green)', controls: [{ key: 'saturation', label: 'Saturation', min: 0, max: 200 }, { key: 'warmth', label: 'Warmth', min: -50, max: 50 }] },
  { name: 'Detail', color: 'var(--blue)', controls: [{ key: 'sharpness', label: 'Sharpness', min: 0, max: 100 }, { key: 'vignette', label: 'Vignette', min: 0, max: 100 }] },
]
export const UPLOAD_LIMITS = { bytes: 10_000_000, pixels: 24_000_000, side: 10_000 }
export type LocalPhoto = { url: string; name: string; width: number; height: number; format: string; local: boolean }

export function inspectFile(bytes: Uint8Array, name: string, size: number): string {
  if (size > UPLOAD_LIMITS.bytes) throw new Error('This photograph exceeds 10 MB. Choose a smaller file.')
  const read = (start: number, count: number) => String.fromCharCode(...bytes.slice(start, start + count))
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
  let format = ''
  if (bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255) format = 'JPEG'
  else if (read(0, 8) === '\x89PNG\r\n\x1a\n') {
    format = 'PNG'
    for (let offset = 8; offset + 12 <= bytes.length;) {
      const length = view.getUint32(offset)
      if (read(offset + 4, 4) === 'acTL') throw new Error('Animated images are not supported. Choose a still JPG, PNG or WebP.')
      offset += length + 12
    }
  } else if (read(0, 4) === 'RIFF' && read(8, 4) === 'WEBP') {
    format = 'WebP'
    for (let offset = 12; offset + 8 <= bytes.length;) {
      const length = view.getUint32(offset + 4, true)
      if (read(offset, 4) === 'ANIM' || read(offset, 4) === 'ANMF') throw new Error('Animated images are not supported. Choose a still JPG, PNG or WebP.')
      offset += 8 + length + (length % 2)
    }
  }
  const extension = name.split('.').pop()?.toLowerCase()
  const expected: Record<string, string> = { jpg: 'JPEG', jpeg: 'JPEG', png: 'PNG', webp: 'WebP' }
  if (!format || !extension || expected[extension] !== format) throw new Error('Choose a still JPG, PNG or WebP with a matching file extension.')
  return format
}

export async function loadPhoto(file: File): Promise<LocalPhoto> {
  if (file.size > UPLOAD_LIMITS.bytes) throw new Error('This photograph exceeds 10 MB. Choose a smaller file.')
  const format = inspectFile(new Uint8Array(await file.arrayBuffer()), file.name, file.size)
  const url = URL.createObjectURL(file)
  try {
    const image = new Image()
    image.src = url
    await image.decode()
    const width = image.naturalWidth, height = image.naturalHeight
    if (!width || !height) throw new Error('Unable to read this photograph. Please choose another image.')
    if (width * height > UPLOAD_LIMITS.pixels || Math.max(width, height) > UPLOAD_LIMITS.side) throw new Error('Choose an image up to 24 megapixels and 10,000 pixels per side.')
    return { url, name: file.name, width, height, format, local: true }
  } catch (error) {
    URL.revokeObjectURL(url)
    if (error instanceof Error && error.name !== 'EncodingError') throw error
    throw new Error('Unable to read this photograph. Please choose another image.')
  }
}
