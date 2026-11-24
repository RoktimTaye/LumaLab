import type { Adjustments } from './editor'
export function toneLut(values: Adjustments): number[] {
  return Array.from({length:256},(_,i)=>{
    const x=Math.max(0,Math.min(1,i/255*2**(values.exposure ?? 0)))
    const y=x+(values.shadows ?? 0)/100*.35*(1-x)**2+(values.highlights ?? 0)/100*.35*x*x+(values.ambience ?? 0)/100*.3*(1-2*x)*(4*x*(1-x))
    return Math.round(Math.max(0,Math.min(1,y))*255)
  })
}
export function toneTable(values: Adjustments): string {
  return toneLut(values).map(value=>value/255).join(' ')
}
export function geometrySize(width:number,height:number,values:Adjustments): [number,number] {
  const a=Math.abs(values.straighten ?? 0)*Math.PI/180
  const scale=Math.min(width/(width*Math.cos(a)+height*Math.sin(a)),height/(height*Math.cos(a)+width*Math.sin(a)))
  const w=Math.max(1,Math.floor(width*scale)),h=Math.max(1,Math.floor(height*scale))
  return (values.rotation ?? 0)%180 ? [h,w] : [w,h]
}
