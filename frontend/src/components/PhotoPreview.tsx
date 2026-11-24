import { Fragment, useId, type CSSProperties } from 'react'
import { NativeTonePreview } from './NativeTonePreview'
import { usePreviewToneMean } from '../lib/usePreviewToneMean'
import { toneTable, geometrySize } from '../lib/manual'
import type { Adjustments } from '../lib/editor'
import type { Crop } from '../lib/crop'
import type { RGBCurves } from '../lib/api'
import { curveValue, identityCurves } from '../lib/curves'
import styles from './Shared.module.css'

export function PhotoPreview({ src, originalSrc = src, values, curves = identityCurves(), name, compare = false, split = 50, onSplit, eager = false, authoritative = false, crop, originalWidth, originalHeight }: { src: string; originalSrc?: string; values: Adjustments; curves?: RGBCurves; name: string; compare?: boolean; split?: number; onSplit?: (value: number) => void; eager?: boolean; authoritative?: boolean; crop?: Crop | null; originalWidth?: number; originalHeight?: number }) {
  const id = `tone-${useId().replace(/:/g, '')}`
  const sharpness = values.sharpness / 100 * 2
  const structure = (values.structure ?? 0) / 100
  const contrastMean = usePreviewToneMean(originalSrc,values,crop,originalWidth,originalHeight)
  const warmth = values.warmth * .4 / 255
  const tint = (values.tint ?? 0) * 0.4 / 255
  const filter = `url(#${id}-tones) brightness(${values.brightness / 100}) url(#${id})`
  const table = (channel: keyof RGBCurves) => Array.from({ length: 256 }, (_, x) => (Math.round(curveValue(curves[channel].points, x)) / 255).toFixed(5)).join(' ')
  const cropped = crop && originalWidth && originalHeight ? {
    position: 'absolute' as const, width: `${originalWidth / crop.width * 100}%`, height: `${originalHeight / crop.height * 100}%`,
    maxWidth: 'none', left: `${-crop.x / crop.width * 100}%`, top: `${-crop.y / crop.height * 100}%`,
  } : undefined
  const width = crop?.width ?? originalWidth
  const height = crop?.height ?? originalHeight
  const dimensions = width && height ? geometrySize(width,height,values) : null
  const frame: CSSProperties | undefined = dimensions && width && height ? {
    position:'absolute', left:'50%', top:'50%', width:`${((values.rotation ?? 0)%180 ? dimensions[1] : dimensions[0])/dimensions[0]*100}%`, height:`${((values.rotation ?? 0)%180 ? dimensions[0] : dimensions[1])/dimensions[1]*100}%`,
    transform:`translate(-50%,-50%) rotate(${values.rotation ?? 0}deg) scale(${values.flip_horizontal ? -1 : 1},${values.flip_vertical ? -1 : 1})`, overflow:'hidden',
  } : undefined
  const straighten: CSSProperties | undefined = dimensions && width && height ? {
    width:'100%',height:'100%',position:'relative',
    transform:`rotate(${values.straighten ?? 0}deg) scale(${1/Math.min(width/(width*Math.cos(Math.abs(values.straighten ?? 0)*Math.PI/180)+height*Math.sin(Math.abs(values.straighten ?? 0)*Math.PI/180)),height/(height*Math.cos(Math.abs(values.straighten ?? 0)*Math.PI/180)+width*Math.sin(Math.abs(values.straighten ?? 0)*Math.PI/180)))})`,
  } : undefined
  // Cropping precedes straightening, flips and quarter-turn rotation on both paths.
  const localImageStyle = { ...cropped, filter, width: cropped?.width ?? '100%', height: cropped?.height ?? '100%' }
  return <div className={styles.photo} style={dimensions ? { aspectRatio:`${dimensions[0]}/${dimensions[1]}` } : cropped && crop ? { aspectRatio: `${crop.width}/${crop.height}` } : undefined}>
    <svg className={styles.filterDefs} aria-hidden="true"><defs>
      <filter id={`${id}-tones`} colorInterpolationFilters="sRGB"><feComponentTransfer><feFuncR type="table" tableValues={toneTable(values)}/><feFuncG type="table" tableValues={toneTable(values)}/><feFuncB type="table" tableValues={toneTable(values)}/></feComponentTransfer></filter>
      <filter id={id} colorInterpolationFilters="sRGB" primitiveUnits="objectBoundingBox" x="-10%" y="-10%" width="120%" height="120%">
        <feComponentTransfer><feFuncR type="linear" slope={values.contrast/100} intercept={contrastMean*(1-values.contrast/100)}/><feFuncG type="linear" slope={values.contrast/100} intercept={contrastMean*(1-values.contrast/100)}/><feFuncB type="linear" slope={values.contrast/100} intercept={contrastMean*(1-values.contrast/100)}/></feComponentTransfer>
        <feColorMatrix type="matrix" values={`${.299+.701*values.saturation/100} ${.587-.587*values.saturation/100} ${.114-.114*values.saturation/100} 0 0 ${.299-.299*values.saturation/100} ${.587+.413*values.saturation/100} ${.114-.114*values.saturation/100} 0 0 ${.299-.299*values.saturation/100} ${.587-.587*values.saturation/100} ${.114+.886*values.saturation/100} 0 0 0 0 0 1 0`}/>
        <feColorMatrix type="matrix" values={`1 0 0 0 ${values.saturation ? warmth : 0} 0 1 0 0 0 0 0 1 0 ${values.saturation ? -warmth : 0} 0 0 0 1 0`}/>
        <feColorMatrix type="matrix" values={`1 0 0 0 ${tint*.5} 0 1 0 0 ${-tint} 0 0 1 0 ${tint*.5} 0 0 0 1 0`}/>
        <feComponentTransfer><feFuncR type="table" tableValues={table('rgb')}/><feFuncG type="table" tableValues={table('rgb')}/><feFuncB type="table" tableValues={table('rgb')}/></feComponentTransfer>
        <feComponentTransfer result="tone"><feFuncR type="table" tableValues={table('red')}/><feFuncG type="table" tableValues={table('green')}/><feFuncB type="table" tableValues={table('blue')}/></feComponentTransfer>
        {[
          {name:'structure',source:'tone',result:'structured',amount:structure,threshold:4,radius:Math.max(width ?? 1,height ?? 1)/400},
          {name:'sharp',source:'structured',result:'detailed',amount:sharpness,threshold:3,radius:Math.max(width ?? 1,height ?? 1)/1600},
        ].map(detail=><Fragment key={detail.name}>
          <feGaussianBlur in={detail.source} stdDeviation={`${detail.radius/(width ?? 1)} ${detail.radius/(height ?? 1)}`} edgeMode="duplicate" result={`${detail.name}Blur`}/>
          <feComposite in={detail.source} in2={`${detail.name}Blur`} operator="arithmetic" k1="0" k2={1+detail.amount} k3={-detail.amount} k4="0" result={`${detail.name}Enhanced`}/>
          <feBlend in={detail.source} in2={`${detail.name}Blur`} mode="difference"/>
          <feColorMatrix type="matrix" values="0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 .299 .587 .114 0 0"/>
          <feComponentTransfer result={`${detail.name}Mask`}><feFuncA type="discrete" tableValues={Array.from({length:256},(_,i)=>i>detail.threshold ? '1':'0').join(' ')}/></feComponentTransfer>
          <feComposite in={`${detail.name}Enhanced`} in2={`${detail.name}Mask`} operator="in"/>
          <feComposite in2={detail.source} operator="over" result={detail.result}/>
        </Fragment>)}
      </filter>
    </defs></svg>
    {dimensions ? <div style={frame}><div style={straighten}><img className={styles.photoBase} style={{ ...cropped, width:cropped?.width ?? '100%', height:cropped?.height ?? '100%' }} src={originalSrc} alt={name}/></div></div> : <img className={styles.photoBase} style={cropped} src={originalSrc} alt={name} loading={eager ? 'eager' : 'lazy'} decoding="async" />}
    <div className={styles.photoEdited} style={{ clipPath: compare ? `inset(0 0 0 ${split}%)` : undefined }}>
      <div style={dimensions ? frame : { position:'absolute', inset:0 }}><div style={dimensions ? straighten : { width:'100%',height:'100%' }}><NativeTonePreview src={originalSrc} values={values} style={{...(dimensions ? localImageStyle : {width:'100%',height:'100%'}),filter:`url(#${id})`}} fallbackFilter={filter}/><div className={styles.vignette} style={{opacity:values.vignette/100,background:'radial-gradient(ellipse farthest-corner at center,rgba(0,0,0,0) 0%,rgba(0,0,0,.04375) 25%,rgba(0,0,0,.175) 50%,rgba(0,0,0,.39375) 75%,rgba(0,0,0,.7) 100%)'}}/></div></div>
      <img src={src} alt="" style={{position:'absolute',inset:0,width:'100%',height:'100%',opacity:authoritative ? 1 : 0,transition:'opacity 120ms linear',pointerEvents:'none'}} loading={eager ? 'eager' : 'lazy'} decoding="sync"/>
    </div>
    {compare && <><span className={styles.beforeLabel}>ORIGINAL</span><span className={styles.afterLabel}>EDITED</span><div className={styles.splitLine} style={{ left: `${split}%` }}><span>‹ ›</span></div>{onSplit && <input className={styles.compareRange} aria-label="Before and after comparison position" type="range" min="0" max="100" step="any" value={split} onChange={e => onSplit(Number(e.target.value))} />}</>}
  </div>
}
