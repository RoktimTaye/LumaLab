import { useEffect, useRef, useState } from 'react'
import { X } from 'lucide-react'
import styles from '../pages/Studio.module.css'
export function WhiteBalancePicker({src,onApply,onClose}:{src:string;onApply:(warmth:number,tint:number)=>void;onClose:()=>void}) {
  const dialog=useRef<HTMLDialogElement>(null),canvas=useRef<HTMLCanvasElement>(null)
  const [ready,setReady]=useState(false),[error,setError]=useState('')
  useEffect(()=>{const focus=document.activeElement as HTMLElement;dialog.current?.showModal();return()=>{dialog.current?.close();focus?.focus()}},[])
  useEffect(()=>{
    let cancelled=false
    const image=new Image()
    image.onload=()=>{
      if(cancelled || !canvas.current)return
      const element=canvas.current,scale=Math.min(1,1000/Math.max(image.width,image.height))
      element.width=Math.max(1,Math.round(image.width*scale));element.height=Math.max(1,Math.round(image.height*scale))
      element.getContext('2d',{willReadFrequently:true})?.drawImage(image,0,0,element.width,element.height);setReady(true)
    }
    image.onerror=()=>{if(!cancelled)setError('Could not load the original preview.')}
    image.src=src
    return()=>{cancelled=true}
  },[src])
  function balance(red:number,green:number,blue:number){const clamp=(x:number)=>Math.round(Math.max(-50,Math.min(50,x)));onApply(clamp((blue-red)/.8),clamp((green-(red+blue)/2)/.6));onClose()}
  function automatic(){
    const element=canvas.current,context=element?.getContext('2d');if(!context||!element)return
    const pixels=context.getImageData(0,0,element.width,element.height).data
    let r=0,g=0,b=0,count=0
    for(let i=0;i<pixels.length;i+=4){const mean=(pixels[i]+pixels[i+1]+pixels[i+2])/3;if(mean<30||mean>225)continue;r+=pixels[i];g+=pixels[i+1];b+=pixels[i+2];count++}
    if(!count){setError('No usable midtones. Choose a neutral point manually.');return}balance(r/count,g/count,b/count)
  }
  return <dialog ref={dialog} className={styles.dialog} onCancel={event=>{event.preventDefault();onClose()}} aria-labelledby="wb-title"><div className={styles.dialogTop}><h2 id="wb-title">White balance</h2><button className="icon-button" onClick={onClose} aria-label="Close white balance"><X size={18}/></button></div><p>Tap an area that should be neutral grey or white. Sampling uses the original photo before your edits.</p>{error&&<p role="alert">{error}</p>}<canvas ref={canvas} aria-label="Original image for neutral colour sampling" style={{display:'block',maxWidth:'100%',maxHeight:'50dvh',width:'auto',height:'auto',cursor:'crosshair',marginInline:'auto'}} onClick={event=>{const element=event.currentTarget,box=element.getBoundingClientRect(),context=element.getContext('2d');if(!context||!ready)return;const x=Math.min(element.width-1,Math.max(0,Math.floor((event.clientX-box.left)/box.width*element.width))),y=Math.min(element.height-1,Math.max(0,Math.floor((event.clientY-box.top)/box.height*element.height)));const pixel=context.getImageData(x,y,1,1).data;if(Math.max(pixel[0],pixel[1],pixel[2])>250||Math.min(pixel[0],pixel[1],pixel[2])<5){setError('Choose a point away from clipped whites and blacks.');return}balance(pixel[0],pixel[1],pixel[2])}}/><div className={styles.whiteBalanceActions}><button className="button secondary" disabled={!ready} onClick={automatic}>Auto white balance</button></div><p>Auto estimates a neutral average from midtones. Fine-tune temperature and tint afterwards.</p></dialog>
}
