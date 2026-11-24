import { useEffect, useMemo, useState } from 'react'
import type { Adjustments } from './editor'
import type { Crop } from './crop'
import { toneLut } from './manual'

// Pillow contrast pivots around the image luminance mean, not CSS's fixed 50%.
export function usePreviewToneMean(src:string,values:Adjustments,crop:Crop|null|undefined,originalWidth?:number,originalHeight?:number){
  const [sample,setSample]=useState<{src:string;pixels:ImageData}|null>(null)
  useEffect(()=>{
    let cancelled=false
    const image=new Image()
    image.onload=()=>{
      if(cancelled)return
      try{
        const scale=1,canvas=document.createElement('canvas')
        canvas.width=Math.max(1,Math.round(image.naturalWidth*scale));canvas.height=Math.max(1,Math.round(image.naturalHeight*scale))
        const context=canvas.getContext('2d',{willReadFrequently:true});if(!context)return
        context.drawImage(image,0,0,canvas.width,canvas.height)
        setSample({src,pixels:context.getImageData(0,0,canvas.width,canvas.height)})
      }catch{/* Keep the neutral pivot if sampling is unavailable. */}
    }
    image.src=src
    return()=>{cancelled=true}
  },[src])
  return useMemo(()=>{
    if(!sample || sample.src!==src)return .5
    const pixels=sample.pixels, data=pixels.data,tones=toneLut(values),brightness=values.brightness/100
    const mapped=(n:number)=>Math.floor(Math.min(255,tones[n]*brightness))
    const x0=crop&&originalWidth ? Math.floor(crop.x/originalWidth*pixels.width):0
    const y0=crop&&originalHeight ? Math.floor(crop.y/originalHeight*pixels.height):0
    const x1=crop&&originalWidth ? Math.max(x0+1,Math.ceil((crop.x+crop.width)/originalWidth*pixels.width)):pixels.width
    const y1=crop&&originalHeight ? Math.max(y0+1,Math.ceil((crop.y+crop.height)/originalHeight*pixels.height)):pixels.height
    let total=0,count=0
    for(let y=y0;y<Math.min(y1,pixels.height);y++)for(let x=x0;x<Math.min(x1,pixels.width);x++){
      const i=(y*pixels.width+x)*4
      total+=Math.round(.299*mapped(data[i])+.587*mapped(data[i+1])+.114*mapped(data[i+2]));count++
    }
    return count ? Math.round(total/count)/255:.5
  },[sample,src,values.exposure,values.highlights,values.shadows,values.ambience,values.brightness,crop,originalWidth,originalHeight])
}
