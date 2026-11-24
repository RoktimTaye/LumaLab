import { useEffect, useMemo, useState } from 'react'
import type { Adjustments, RGBCurves } from '../lib/api'
import type { Crop } from '../lib/crop'
import { histogramData, livePixels, type HistogramData } from '../lib/liveHistogram'
import styles from './Histogram.module.css'

function sample(image:HTMLImageElement,crop:Crop|null=null,originalWidth=0,originalHeight=0,straighten=0):ImageData {
  const canvas=document.createElement('canvas')
  const width=crop?.width ?? image.naturalWidth,height=crop?.height ?? image.naturalHeight
  const scale=Math.min(1,192/Math.max(width,height))
  canvas.width=Math.max(1,Math.round(width*scale));canvas.height=Math.max(1,Math.round(height*scale))
  const context=canvas.getContext('2d',{willReadFrequently:true});if(!context)throw new Error('Canvas unavailable')
  const angle=straighten*Math.PI/180
  const trim=Math.min(width/(width*Math.cos(Math.abs(angle))+height*Math.sin(Math.abs(angle))),height/(height*Math.cos(Math.abs(angle))+width*Math.sin(Math.abs(angle))))
  context.translate(canvas.width/2,canvas.height/2);context.rotate(angle);context.scale(1/trim,1/trim)
  const sx=crop && originalWidth ? image.naturalWidth/originalWidth : 1,sy=crop && originalHeight ? image.naturalHeight/originalHeight : 1
  context.drawImage(image,(crop?.x ?? 0)*sx,(crop?.y ?? 0)*sy,crop ? crop.width*sx : image.naturalWidth,crop ? crop.height*sy : image.naturalHeight,-canvas.width/2,-canvas.height/2,canvas.width,canvas.height)
  return context.getImageData(0,0,canvas.width,canvas.height)
}

export function Histogram({src,originalSrc,updating,values,curves,crop,originalWidth,originalHeight}:{src:string;originalSrc:string;updating:boolean;values:Adjustments;curves:RGBCurves;crop:Crop|null;originalWidth:number;originalHeight:number}) {
  const [original,setOriginal]=useState<{src:string;image:HTMLImageElement}|null>(null)
  const [rendered,setRendered]=useState<{src:string;data:HistogramData}|null>(null)
  const [failed,setFailed]=useState(false)
  useEffect(()=>{
    let cancelled=false;setFailed(false)
    const image=new Image()
    image.onload=()=>{if(!cancelled)setOriginal({src:originalSrc,image})}
    image.onerror=()=>{if(!cancelled)setFailed(true)}
    image.src=originalSrc;return()=>{cancelled=true}
  },[originalSrc])
  useEffect(()=>{
    if(updating)return
    let cancelled=false
    const image=new Image()
    image.onload=()=>{if(cancelled)return;try{setRendered({src,data:histogramData(sample(image).data)});setFailed(false)}catch{setFailed(true)}}
    image.onerror=()=>{if(!cancelled)setFailed(true)}
    image.src=src;return()=>{cancelled=true}
  },[src,updating])
  const live=useMemo(()=>{
    if(!original || original.src!==originalSrc)return null
    if(!updating && rendered?.src===src)return null
    try{const image=sample(original.image,crop,originalWidth,originalHeight,values.straighten ?? 0);return histogramData(livePixels(image.data,image.width,image.height,values,curves))}catch{return null}
  },[original,originalSrc,values,curves,crop,originalWidth,originalHeight,updating,rendered,src])
  const isLive=updating || rendered?.src!==src
  const data=isLive ? live : rendered?.data
  const peak=data ? Math.max(1,...data.bins):1
  return <section className={styles.histogram} aria-label="Photo histogram">
    <div className={styles.heading}>Histogram{isLive && data && <span title="Instant local estimate; refined when the server render is ready">Live</span>}</div>
    {failed && !data ? <p>Histogram unavailable.</p> : !data ? <p>Reading preview…</p> : <>
      <svg viewBox="0 0 256 80" role="img" aria-label="Luminance histogram, shadows on the left and highlights on the right" className={styles.graph}>
        <path fill="currentColor" d={`M0 80 ${data.bins.map((n,i)=>`L${i} ${80-n/peak*76}`).join(' ')} L255 80 Z`}/>
      </svg>
      <p className={styles.clipping} title={isLive ? 'Estimated clipping from the live local preview.' : 'Clipping measured from the rendered JPEG preview.'}><span>Shadows {data.dark.toFixed(1)}%</span><span>Highlights {data.light.toFixed(1)}%</span></p>
    </>}
  </section>
}
