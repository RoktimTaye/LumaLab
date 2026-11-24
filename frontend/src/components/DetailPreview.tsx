import { useEffect, useId, useRef, useState } from 'react'
import { LoaderCircle, X } from 'lucide-react'
import { exportImage, type Adjustments, type RGBCurves, type NaturalEnhancement } from '../lib/api'
import type { Crop } from '../lib/crop'
import styles from './DetailPreview.module.css'

export function DetailPreview({ imageId, token, adjustments, enhancement, curves, crop, onClose, returnFocusTo }: {
  imageId: string; token: string; adjustments: Adjustments; enhancement: NaturalEnhancement | null
  curves?: RGBCurves; crop: Crop | null; onClose: () => void; returnFocusTo: HTMLElement | null
}) {
  const id = useId()
  const dialog = useRef<HTMLDialogElement>(null)
  const viewport = useRef<HTMLDivElement>(null)
  const trigger = useRef(returnFocusTo)
  const [url, setUrl] = useState('')
  const [error, setError] = useState('')
  const [dimensions, setDimensions] = useState('')

  useEffect(() => {
    const element = dialog.current
    element?.showModal()
    return () => {
      element?.close()
      window.requestAnimationFrame(() => {
        if (!element?.open && trigger.current?.isConnected) trigger.current.focus()
      })
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    let objectUrl = ''
    setUrl(''); setError(''); setDimensions('')
    // Use the actual export path: geometry, manual settings and source-scale
    // detail are identical to the downloadable JPEG, rather than a resized proxy.
    // Defer dispatch one task so StrictMode's setup/cleanup probe cannot start
    // a duplicate expensive render whose abandoned request holds the permit.
    const timer = window.setTimeout(() => { void exportImage(imageId, token, adjustments, controller.signal, crop, enhancement, curves).then(result => {
      if (controller.signal.aborted) return
      if (result.blob.type !== 'image/jpeg') throw new Error('The detail response was not a JPEG.')
      objectUrl = URL.createObjectURL(result.blob)
      setUrl(objectUrl)
    }).catch(caught => {
      if (!controller.signal.aborted) setError(caught instanceof Error ? caught.message : 'Unable to prepare the detail view.')
    }) }, 0)
    return () => { window.clearTimeout(timer); controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl) }
  }, [imageId, token, adjustments, crop, enhancement, curves])

  return <dialog ref={dialog} className={styles.dialog} aria-labelledby={id} aria-describedby={`${id}-description`}
    onCancel={event => { event.preventDefault(); onClose() }}>
    <div className={styles.header}><h2 id={id}>100% detail</h2><button className="icon-button" onClick={onClose} aria-label="Close detail view"><X size={18}/></button></div>
    <p id={`${id}-description`}>Full-resolution export preview. Scroll to inspect fine texture; this view can take a little longer to prepare.</p>
    {error ? <p role="alert" className={styles.error}>{error}</p> : !url ? <div role="status" className={styles.loading}><LoaderCircle size={22}/><span>Preparing full-resolution detail…</span></div> :
      <div ref={viewport} className={styles.viewport} tabIndex={0} aria-label="Full-resolution photograph; scroll to inspect detail">
        <img className={styles.image} src={url} alt="Full-resolution enhanced photograph" onError={() => setError('Unable to display the detail image. Close this view and try again.')} onLoad={event => {
          const image = event.currentTarget
          setDimensions(`${image.naturalWidth} × ${image.naturalHeight}`)
          if (viewport.current) {
            viewport.current.scrollLeft = Math.max(0, (image.naturalWidth - viewport.current.clientWidth) / 2)
            viewport.current.scrollTop = Math.max(0, (image.naturalHeight - viewport.current.clientHeight) / 2)
          }
        }}/>
      </div>}
    {dimensions && <p className={styles.meta}>{dimensions} · 100% view · current crop and settings</p>}
  </dialog>
}
