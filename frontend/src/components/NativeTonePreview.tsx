import { useEffect, useLayoutEffect, useRef, useState, type CSSProperties } from 'react'
import type { Adjustments } from '../lib/editor'
import { toneLut } from '../lib/manual'

// Apply nonlinear tones at the preview source resolution, before CSS scales
// pixels for display. Applying a clipped exposure LUT to already-scaled pixels
// cannot match the backend's order and causes a visible change at mouse-up.
export function NativeTonePreview({src,values,style,fallbackFilter}:{src:string;values:Adjustments;style:CSSProperties;fallbackFilter:string}) {
  const canvas=useRef<HTMLCanvasElement>(null)
  const [viewport,setViewport]=useState({width:0,height:0})
  useEffect(()=>{
    const element=canvas.current;if(!element)return
    const observer=new ResizeObserver(()=>setViewport({width:element.clientWidth,height:element.clientHeight}))
    observer.observe(element);return()=>observer.disconnect()
  },[])
  const [source,setSource]=useState<{src:string;image:ImageData}|null>(null)
  useEffect(()=>{
    let cancelled=false
    const image=new Image()
    image.onload=()=>{
      if(cancelled)return
      try {
        const buffer=document.createElement('canvas');buffer.width=image.naturalWidth;buffer.height=image.naturalHeight
        const context=buffer.getContext('2d',{willReadFrequently:true});if(!context)return
        context.drawImage(image,0,0)
        setSource({src,image:context.getImageData(0,0,buffer.width,buffer.height)})
      } catch { /* The ordinary image remains available if canvas is unavailable. */ }
    }
    image.src=src
    return()=>{cancelled=true}
  },[src])
  const ready=source?.src===src
  useLayoutEffect(()=>{
    if(!source || source.src!==src || !canvas.current)return
    const element=canvas.current,buffer=document.createElement('canvas')
    buffer.width=source.image.width;buffer.height=source.image.height
    const nativeContext=buffer.getContext('2d');if(!nativeContext)return
    element.width=Math.min(buffer.width,Math.max(1,Math.round(element.clientWidth*(window.devicePixelRatio||1))))
    element.height=Math.min(buffer.height,Math.max(1,Math.round(element.clientHeight*(window.devicePixelRatio||1))))
    const context=element.getContext('2d');if(!context)return
    const table=toneLut(values).map(value=>Math.max(0,Math.min(255,Math.floor(value*values.brightness/100))))
    const output=nativeContext.createImageData(source.image.width,source.image.height),input=source.image.data
    for(let i=0;i<input.length;i+=4){output.data[i]=table[input[i]];output.data[i+1]=table[input[i+1]];output.data[i+2]=table[input[i+2]];output.data[i+3]=255}
    nativeContext.putImageData(output,0,0)
    context.imageSmoothingEnabled=true
    context.imageSmoothingQuality='high'
    context.drawImage(buffer,0,0,element.width,element.height)
  },[source,src,values.exposure,values.highlights,values.shadows,values.ambience,values.brightness,viewport.width,viewport.height])
  return <><img src={src} alt="" style={{...style,filter:fallbackFilter,visibility:ready?'hidden':'visible'}} decoding="sync"/><canvas ref={canvas} aria-hidden="true" style={{...style,display:'block',position:'absolute',left:style.left ?? 0,top:style.top ?? 0,visibility:ready?'visible':'hidden'}}/></>
}
