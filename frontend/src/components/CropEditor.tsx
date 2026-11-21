import { useEffect, useRef, useState, type PointerEvent } from 'react'
import { ASPECT_RATIOS, clamp, fitCrop, moveCrop, resizeCrop, type Crop } from '../lib/crop'
import styles from './CropEditor.module.css'

export function CropEditor({ src, width, height, crop, onApply, onCancel }: {
  src: string; width: number; height: number; crop: Crop | null
  onApply: (crop: Crop | null) => void; onCancel: () => void
}) {
  const [draft, setDraft] = useState<Crop>(() => crop ?? fitCrop(width, height, null))
  const [aspect, setAspect] = useState('free')
  const dialog = useRef<HTMLDialogElement>(null)
  const trigger = useRef(document.activeElement as HTMLElement | null)
  const stage = useRef<HTMLDivElement>(null)
  const gesture = useRef<{ x: number; y: number; crop: Crop; corner: string; pointerId: number; scaleX: number; scaleY: number } | null>(null)
  const ratio = aspect === 'original' ? width / height : ASPECT_RATIOS.find(item => item.value === aspect)?.ratio ?? null

  useEffect(() => {
    const element = dialog.current
    element?.showModal()
    return () => { element?.close(); window.requestAnimationFrame(() => trigger.current?.focus()) }
  }, [])

  function start(event: PointerEvent<HTMLButtonElement>, corner: string) {
    if (!event.isPrimary || event.button !== 0 || !stage.current) return
    event.preventDefault()
    const rect = stage.current.getBoundingClientRect()
    gesture.current = { x: event.clientX, y: event.clientY, crop: draft, corner, pointerId: event.pointerId, scaleX: width / rect.width, scaleY: height / rect.height }
    event.currentTarget.setPointerCapture(event.pointerId)
  }
  function move(event: PointerEvent<HTMLButtonElement>) {
    const drag = gesture.current
    if (!drag || event.pointerId !== drag.pointerId) return
    const dx = (event.clientX - drag.x) * drag.scaleX, dy = (event.clientY - drag.y) * drag.scaleY
    setDraft(drag.corner === 'move' ? moveCrop(drag.crop, drag.crop.x + dx, drag.crop.y + dy, width, height)
      : resizeCrop(drag.crop, dx, dy, drag.corner, width, height, ratio))
  }
  function input(key: keyof Crop, value: number) {
    if (!Number.isFinite(value)) return
    if (key === 'x' || key === 'y') setDraft(moveCrop(draft, key === 'x' ? value : draft.x, key === 'y' ? value : draft.y, width, height))
    else setDraft(resizeCrop(draft, key === 'width' ? value - draft.width : 0, key === 'height' ? value - draft.height : 0, 'se', width, height, ratio))
  }
  function apply() {
    onApply(draft.x === 0 && draft.y === 0 && draft.width === width && draft.height === height ? null : draft)
  }
  return <dialog ref={dialog} className={styles.dialog} aria-labelledby="crop-title" aria-describedby="crop-help" onCancel={event => { event.preventDefault(); onCancel() }}>
    <div className={styles.heading}><h2 id="crop-title">Crop & aspect ratio</h2><button className="button secondary" onClick={onCancel} aria-label="Close crop editor">Close</button></div>
    <p id="crop-help">Drag the frame to move it, or drag a corner to resize. Use the pixel controls for precise edits.</p>
    <div className={styles.options}><label htmlFor="crop-ratio">Aspect ratio</label><select id="crop-ratio" value={aspect} onChange={event => {
      const value = event.target.value
      setAspect(value)
      if (value !== 'free') setDraft(fitCrop(width, height, value === 'original' ? width / height : ASPECT_RATIOS.find(item => item.value === value)?.ratio ?? null))
    }}>{ASPECT_RATIOS.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</select></div>
    <div className={styles.canvas}><div ref={stage} className={styles.stage} style={{ aspectRatio: `${width}/${height}`, width: `min(100%, calc(48vh * ${width / height}))` }}>
      <img src={src} alt="Original photograph for crop selection" draggable={false}/>
      <div className={styles.selection} style={{ left: `${draft.x / width * 100}%`, top: `${draft.y / height * 100}%`, width: `${draft.width / width * 100}%`, height: `${draft.height / height * 100}%` }}>
        <button className={styles.move} aria-label="Move crop selection" onPointerDown={event => start(event, 'move')} onPointerMove={move} onPointerUp={() => { gesture.current = null }} onPointerCancel={() => { gesture.current = null }} onLostPointerCapture={() => { gesture.current = null }} onKeyDown={event => {
          const arrows: Record<string, [number, number]> = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }
          const delta = arrows[event.key]
          if (delta) { event.preventDefault(); const step = event.shiftKey ? 10 : 1; setDraft(moveCrop(draft, draft.x + delta[0] * step, draft.y + delta[1] * step, width, height)) }
        }}/>
        {['nw', 'ne', 'sw', 'se'].map(corner => <button key={corner} tabIndex={-1} aria-label={`Resize crop ${corner}`} className={`${styles.handle} ${styles[corner]}`} onPointerDown={event => start(event, corner)} onPointerMove={move} onPointerUp={() => { gesture.current = null }} onPointerCancel={() => { gesture.current = null }} onLostPointerCapture={() => { gesture.current = null }}/>) }
      </div>
    </div></div>
    <div className={styles.fields}>{(['x', 'y', 'width', 'height'] as const).map(key => <label key={key} htmlFor={`crop-${key}`}>{({ x: 'Left', y: 'Top', width: 'Width', height: 'Height' })[key]} (px)<input id={`crop-${key}`} type="number" inputMode="numeric" min={key === 'x' || key === 'y' ? 0 : 1} max={key === 'x' ? width - draft.width : key === 'y' ? height - draft.height : key === 'width' ? width - draft.x : height - draft.y} value={draft[key]} onChange={event => input(key, event.currentTarget.valueAsNumber)}/></label>)}</div>
    <div className={styles.actions}><button className="button secondary" onClick={() => { setAspect('free'); setDraft(fitCrop(width, height, null)) }}>Reset crop</button><span aria-live="polite">{clamp(draft.width, 1, width)} × {clamp(draft.height, 1, height)} px</span><button className="button secondary" onClick={onCancel}>Cancel</button><button className="button primary" onClick={apply}>Apply crop</button></div>
  </dialog>
}
