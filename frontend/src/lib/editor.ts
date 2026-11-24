import type { components } from './api.generated'

export type Adjustments = components['schemas']['Adjustments']
export type AdjustmentKey = keyof Adjustments
export type Preset = { name: string; description: string; values: Adjustments; category: string; popular?: boolean }
export const NEUTRAL: Adjustments = { brightness: 100, contrast: 100, saturation: 100, warmth: 0, sharpness: 0, vignette: 0 }
const preset = (name: string, description: string, category: string, brightness: number, contrast: number, saturation: number, warmth: number, sharpness: number, vignette: number, popular = false): Preset => ({ name, description, category, popular, values: { brightness, contrast, saturation, warmth, sharpness, vignette } })
export const PRESETS: Preset[] = [
  preset('Original', 'Just as you captured it', 'Essentials', 100, 100, 100, 0, 0, 0, true),
  preset('Golden Hour', 'Warm light and a soft glow', 'Popular', 110, 94, 112, 22, 5, 8, true),
  preset('Cinematic', 'Cool tones. Quiet drama.', 'Popular', 98, 120, 78, -12, 12, 22, true),
  preset('Vivid', 'Colour with confidence', 'Popular', 103, 110, 140, 2, 30, 0, true),
  preset('Soft Portrait', 'Gentle warmth and flattering light', 'Popular', 106, 96, 92, 8, 4, 4, true),
  preset('Nordic', 'Airy, cool and understated', 'Popular', 108, 92, 82, -8, 8, 0, true),
  preset('Monochrome', 'A story in light and shadow', 'Black & White', 102, 125, 0, 0, 18, 16, true),
  preset('Warm Portrait', 'Rich skin tones with soft contrast', 'Portrait', 105, 96, 105, 14, 4, 6),
  preset('Studio Glow', 'Bright, polished studio light', 'Portrait', 112, 92, 96, 4, 8, 0),
  preset('Moody Portrait', 'Deeper shadows and a quiet mood', 'Portrait', 94, 116, 88, -4, 8, 18),
  preset('Peach Skin', 'Subtle peach warmth', 'Portrait', 108, 94, 104, 12, 2, 2),
  preset('Classic Portrait', 'Natural colour with crisp detail', 'Portrait', 102, 105, 100, 2, 15, 4),
  preset('Soft Focus', 'Lifted light and gentle detail', 'Portrait', 108, 90, 90, 5, 0, 0),
  preset('Alpine Air', 'Cool clarity for mountain scenes', 'Landscape', 108, 108, 108, -8, 22, 0),
  preset('Deep Forest', 'Earthy greens and shaded depth', 'Landscape', 96, 116, 108, -4, 18, 12),
  preset('Ocean Blue', 'Cool blues with clean contrast', 'Landscape', 104, 110, 112, -14, 16, 0),
  preset('Desert Sand', 'Sun baked warmth and texture', 'Landscape', 108, 104, 106, 18, 18, 4),
  preset('Lush Green', 'Fresh foliage and lively colour', 'Landscape', 103, 106, 126, 3, 14, 0),
  preset('Overcast Lift', 'Bring detail back to cloudy scenes', 'Landscape', 116, 96, 102, 2, 12, 0),
  preset('Retro Film', 'Faded colour with a warm cast', 'Film & Vintage', 104, 88, 82, 12, 3, 14),
  preset('Kodak Warmth', 'Golden film inspired tones', 'Film & Vintage', 106, 104, 108, 16, 8, 8),
  preset('Faded Matte', 'Soft blacks and muted colour', 'Film & Vintage', 108, 86, 78, 4, 0, 10),
  preset('Instant', 'A nostalgic instant film feel', 'Film & Vintage', 110, 92, 88, 9, 2, 12),
  preset('Teal & Amber', 'Cool shadows, warm highlights', 'Film & Vintage', 100, 118, 104, -6, 10, 18),
  preset('Night Drive', 'Deep contrast for after dark', 'Film & Vintage', 92, 130, 88, -10, 12, 28),
  preset('Silver Gelatin', 'Crisp black and white detail', 'Black & White', 102, 132, 0, 0, 22, 10),
  preset('Soft Mono', 'Gentle grayscale and lifted light', 'Black & White', 110, 92, 0, 0, 4, 0),
  preset('Noir', 'Bold shadows and bright highlights', 'Black & White', 96, 142, 0, -2, 20, 32),
  preset('Warm Mono', 'Sepia inspired monochrome', 'Black & White', 104, 108, 0, 18, 8, 12),
  preset('Blue Hour', 'A quiet blue cast', 'Creative', 94, 112, 92, -18, 8, 20),
  preset('Pastel Dream', 'Light, airy pastel colour', 'Creative', 114, 86, 94, 8, 0, 0),
  preset('Neon Pop', 'Electric colour and contrast', 'Creative', 102, 128, 156, -4, 12, 8),
  preset('Muted Earth', 'Quiet greens and warm neutrals', 'Creative', 100, 98, 78, 9, 10, 5),
  preset('Rose Fade', 'Soft rose warmth', 'Creative', 106, 90, 96, 14, 0, 8),
  preset('High Key', 'Bright, clean and open', 'Creative', 120, 90, 96, 2, 6, 0),
]
export const PRESET_GROUPS = [
  { name: 'Most Popular', presets: PRESETS.filter(item => item.popular) },
  ...['Portrait', 'Landscape', 'Film & Vintage', 'Black & White', 'Creative', 'Essentials'].map(name => ({ name, presets: PRESETS.filter(item => item.category === name && (name === 'Essentials' || !item.popular)) })),
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
