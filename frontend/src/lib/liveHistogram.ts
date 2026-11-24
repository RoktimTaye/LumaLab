import type { Adjustments } from './editor'
import type { RGBCurves } from './api'
import { curveValue } from './curves'
import { toneLut } from './manual'

export type HistogramData = { bins: number[]; dark: number; light: number }
const clamp=(x:number)=>Math.max(0,Math.min(255,x))
const lookup=(table:number[],x:number)=>{const v=clamp(x),i=Math.floor(v);return table[i]+(table[Math.min(255,i+1)]-table[i])*(v-i)}

// A bounded, local approximation of the browser preview filters. The settled
// histogram always comes from the authoritative server JPEG, never this proxy.
export function livePixels(source:Uint8ClampedArray,width:number,height:number,values:Adjustments,curves:RGBCurves):Uint8ClampedArray {
  const tones=toneLut(values),brightness=values.brightness/100,contrast=values.contrast/100,saturation=values.saturation/100
  const warmth=values.warmth/50*.11*255,tint=(values.tint ?? 0)*.4
  const pixels=new Float32Array(source.length)
  for(let i=0;i<source.length;i+=4){
    const r=clamp((clamp(tones[source[i]]*brightness)-127.5)*contrast+127.5)
    const g=clamp((clamp(tones[source[i+1]]*brightness)-127.5)*contrast+127.5)
    const b=clamp((clamp(tones[source[i+2]]*brightness)-127.5)*contrast+127.5)
    const luma=.213*r+.715*g+.072*b
    pixels[i]=clamp(clamp(luma+(r-luma)*saturation)+warmth)
    pixels[i+1]=clamp(clamp(luma+(g-luma)*saturation)+warmth*.25)
    pixels[i+2]=clamp(clamp(luma+(b-luma)*saturation)-warmth)
  }
  const master=Array.from({length:256},(_,i)=>curveValue(curves.rgb.points,i))
  const channels=['red','green','blue'].map(channel=>Array.from({length:256},(_,i)=>curveValue(curves[channel as 'red'|'green'|'blue'].points,i)))
  const sharpness=(values.sharpness+(values.structure ?? 0)*.4)/100*.65
  const output=new Uint8ClampedArray(source.length)
  for(let y=0;y<height;y++)for(let x=0;x<width;x++){
    const index=(y*width+x)*4
    // Approximate the CSS radial vignette at the sampled output coordinates.
    const radius=Math.sqrt(((x+.5-width/2)/(width/2))**2+((y+.5-height/2)/(height/2))**2)/Math.SQRT2
    const vignette=1-values.vignette/100*.9*Math.max(0,Math.min(1,(radius-.27)/.73))
    for(let c=0;c<3;c++){
      const near=pixels[(y*width+Math.max(0,x-1))*4+c]+pixels[(y*width+Math.min(width-1,x+1))*4+c]+pixels[(Math.max(0,y-1)*width+x)*4+c]+pixels[(Math.min(height-1,y+1)*width+x)*4+c]
      const detail=clamp(pixels[index+c]*(1+4*sharpness)-near*sharpness)
      const balanced=clamp(detail+(c===1 ? -tint : tint*.5))
      output[index+c]=lookup(channels[c],lookup(master,balanced))*vignette
    }
    output[index+3]=255
  }
  return output
}
export function histogramData(pixels:Uint8ClampedArray):HistogramData {
  const bins=Array<number>(256).fill(0);let dark=0,light=0
  for(let i=0;i<pixels.length;i+=4){bins[Math.round(.2126*pixels[i]+.7152*pixels[i+1]+.0722*pixels[i+2])]++;if(Math.min(pixels[i],pixels[i+1],pixels[i+2])===0)dark++;if(Math.max(pixels[i],pixels[i+1],pixels[i+2])===255)light++}
  const total=Math.max(1,pixels.length/4)
  return {bins,dark:dark/total*100,light:light/total*100}
}
