import { useId } from 'react'
import type { Adjustments } from '../lib/editor'
import type { Crop } from '../lib/crop'
import type { RGBCurves } from '../lib/api'
import { curveValue, identityCurves } from '../lib/curves'
import styles from './Shared.module.css'

export function PhotoPreview({ src, originalSrc = src, values, curves = identityCurves(), name, compare = false, split = 50, onSplit, eager = false, authoritative = false, crop, originalWidth, originalHeight }: { src: string; originalSrc?: string; values: Adjustments; curves?: RGBCurves; name: string; compare?: boolean; split?: number; onSplit?: (value: number) => void; eager?: boolean; authoritative?: boolean; crop?: Crop | null; originalWidth?: number; originalHeight?: number }) {
  const id = `tone-${useId().replace(/:/g, '')}`
  const sharpness = values.sharpness / 100 * 0.65
  const warmth = values.warmth / 50 * 0.11
  const filter = `brightness(${values.brightness / 100}) contrast(${values.contrast / 100}) saturate(${values.saturation / 100}) url(#${id})`
  const table = (channel: keyof RGBCurves) => Array.from({ length: 256 }, (_, x) => (curveValue(curves[channel].points, x) / 255).toFixed(4)).join(' ')
  const identity = Array.from({ length: 256 }, (_, x) => (x / 255).toFixed(4)).join(' ')
  const cropped = crop && originalWidth && originalHeight ? {
    position: 'absolute' as const, width: `${originalWidth / crop.width * 100}%`, height: `${originalHeight / crop.height * 100}%`,
    maxWidth: 'none', left: `${-crop.x / crop.width * 100}%`, top: `${-crop.y / crop.height * 100}%`,
  } : undefined
  return <div className={styles.photo} style={cropped && crop ? { aspectRatio: `${crop.width}/${crop.height}` } : undefined}>
    <svg className={styles.filterDefs} aria-hidden="true"><defs><filter id={id} colorInterpolationFilters="sRGB"><feColorMatrix type="matrix" values={`1 0 0 0 ${warmth} 0 1 0 0 ${warmth * .25} 0 0 1 0 ${-warmth} 0 0 0 1 0`} /><feConvolveMatrix order="3" kernelMatrix={`0 ${-sharpness} 0 ${-sharpness} ${1 + sharpness * 4} ${-sharpness} 0 ${-sharpness} 0`} preserveAlpha="true" /><feComponentTransfer><feFuncR type="table" tableValues={table('rgb')} /><feFuncG type="table" tableValues={table('rgb')} /><feFuncB type="table" tableValues={table('rgb')} /></feComponentTransfer><feComponentTransfer><feFuncR type="table" tableValues={table('red')} /><feFuncG type="table" tableValues={identity} /><feFuncB type="table" tableValues={identity} /></feComponentTransfer><feComponentTransfer><feFuncR type="table" tableValues={identity} /><feFuncG type="table" tableValues={table('green')} /><feFuncB type="table" tableValues={identity} /></feComponentTransfer><feComponentTransfer><feFuncR type="table" tableValues={identity} /><feFuncG type="table" tableValues={identity} /><feFuncB type="table" tableValues={table('blue')} /></feComponentTransfer></filter></defs></svg>
    <img className={styles.photoBase} style={cropped} src={originalSrc} alt={name} loading={eager ? 'eager' : 'lazy'} decoding="async" />
    <div className={styles.photoEdited} style={{ clipPath: compare ? `inset(0 0 0 ${split}%)` : undefined }}>
      <img src={src} alt="" style={authoritative ? undefined : { filter }} loading={eager ? 'eager' : 'lazy'} />
      {!authoritative && <div className={styles.vignette} style={{ opacity: values.vignette / 100 }} />}
    </div>
    {compare && <><span className={styles.beforeLabel}>ORIGINAL</span><span className={styles.afterLabel}>EDITED</span><div className={styles.splitLine} style={{ left: `${split}%` }}><span>‹ ›</span></div>{onSplit && <input className={styles.compareRange} aria-label="Before and after comparison position" type="range" min="0" max="100" step="any" value={split} onChange={e => onSplit(Number(e.target.value))} />}</>}
  </div>
}
