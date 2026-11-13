import { useId } from 'react'
import type { Adjustments } from '../lib/editor'
import styles from './Shared.module.css'

export function PhotoPreview({ src, values, name, compare = false, split = 50, onSplit, eager = false }: { src: string; values: Adjustments; name: string; compare?: boolean; split?: number; onSplit?: (value: number) => void; eager?: boolean }) {
  const id = `tone-${useId().replace(/:/g, '')}`
  const sharpness = values.sharpness / 100 * 0.65
  const warmth = values.warmth / 50 * 0.11
  const filter = `brightness(${values.brightness / 100}) contrast(${values.contrast / 100}) saturate(${values.saturation / 100}) url(#${id})`
  return <div className={styles.photo}>
    <svg className={styles.filterDefs} aria-hidden="true"><defs><filter id={id} colorInterpolationFilters="sRGB"><feColorMatrix type="matrix" values={`1 0 0 0 ${warmth} 0 1 0 0 ${warmth * .25} 0 0 1 0 ${-warmth} 0 0 0 1 0`} /><feConvolveMatrix order="3" kernelMatrix={`0 ${-sharpness} 0 ${-sharpness} ${1 + sharpness * 4} ${-sharpness} 0 ${-sharpness} 0`} preserveAlpha="true" /></filter></defs></svg>
    <img className={styles.photoBase} src={src} alt={name} loading={eager ? 'eager' : 'lazy'} decoding="async" />
    <div className={styles.photoEdited} style={{ clipPath: compare ? `inset(0 0 0 ${split}%)` : undefined }}>
      <img src={src} alt="" style={{ filter }} loading={eager ? 'eager' : 'lazy'} />
      <div className={styles.vignette} style={{ opacity: values.vignette / 100 }} />
    </div>
    {compare && <><span className={styles.beforeLabel}>ORIGINAL</span><span className={styles.afterLabel}>EDITED</span><div className={styles.splitLine} style={{ left: `${split}%` }}><span>‹ ›</span></div>{onSplit && <input className={styles.compareRange} aria-label="Before and after comparison position" type="range" min="0" max="100" value={split} onChange={e => onSplit(Number(e.target.value))} />}</>}
  </div>
}
