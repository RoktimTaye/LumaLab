import { useId, useRef, useState, type CSSProperties, type PointerEvent } from 'react'
import { RotateCcw } from 'lucide-react'
import type { RGBCurves } from '../lib/api'
import { CHANNELS, curveValue, identityCurves, type CurveChannel } from '../lib/curves'
import styles from './RGBCurveEditor.module.css'

const COLORS = { rgb: '#e4ece6', red: '#ff8d96', green: '#94f7bc', blue: '#8ebcff' }
const LABELS = { rgb: 'RGB', red: 'Red', green: 'Green', blue: 'Blue' }

export function RGBCurveEditor({ value, disabled, onChange, onCommit }: {
  value: RGBCurves; disabled: boolean; onChange: (value: RGBCurves) => void; onCommit: () => void
}) {
  const id = useId()
  const [channel, setChannel] = useState<CurveChannel>('rgb')
  const [selected, setSelected] = useState(0)
  const graph = useRef<HTMLDivElement>(null)
  const drag = useRef<number | null>(null)
  const points = value[channel].points
  const index = Math.min(selected, points.length - 1)
  const point = points[index]
  function update(index: number, x: number, y: number) {
    const next = points.map((p, i) => i !== index ? p : {
      x: i === 0 || i === points.length - 1 ? p.x : Math.max(points[i-1].x + 1, Math.min(points[i+1].x - 1, Math.round(x))),
      y: Math.max(0, Math.min(255, Math.round(y))),
    })
    onChange({ ...value, [channel]: { points: next } })
  }
  function position(event: PointerEvent) {
    const box = graph.current!.getBoundingClientRect()
    return { x: Math.max(0, Math.min(255, Math.round((event.clientX-box.left)/box.width*255))),
      y: Math.max(0, Math.min(255, Math.round((box.bottom-event.clientY)/box.height*255))) }
  }
  function remove(pointIndex = index) {
    if (pointIndex === 0 || pointIndex === points.length - 1) return
    onChange({ ...value, [channel]: { points: points.filter((_, i) => i !== pointIndex) } })
    setSelected(Math.max(0, pointIndex - 1))
    onCommit()
  }
  function addPoint() {
    if (points.length >= 16) return
    let gap = 0
    for (let i = 1; i < points.length - 1; i++) {
      if (points[i+1].x - points[i].x > points[gap+1].x - points[gap].x) gap = i
    }
    const x = Math.round((points[gap].x + points[gap+1].x) / 2)
    const next = [...points.slice(0,gap+1), { x, y: Math.round(curveValue(points,x)) }, ...points.slice(gap+1)]
    setSelected(gap+1)
    onChange({ ...value, [channel]: { points: next } })
  }
  return <details className={styles.section}>
    <summary>RGB Curves<span>POINT CURVE</span></summary>
    <fieldset disabled={disabled} className={styles.controls}>
      <legend className="sr-only">RGB curve controls</legend>
      <div className={styles.channels} role="group" aria-label="Curve channel">
        {CHANNELS.map(key => <button type="button" key={key} aria-pressed={channel === key} style={{ '--curve-color': COLORS[key] } as CSSProperties}
          onClick={() => { setChannel(key); setSelected(0) }}>{LABELS[key]}</button>)}
      </div>
      <p id={`${id}-help`} className={styles.help}>Click to add a point. Drag to shape. Arrow keys adjust; Delete removes.</p>
      <div ref={graph} className={styles.graph} style={{ '--curve-color': COLORS[channel] } as CSSProperties}
        onPointerDown={event => {
          if (disabled || event.button !== 0 || event.target !== event.currentTarget && (event.target as Element).closest('button')) return
          const p = position(event)
          const near = points.findIndex(v => Math.abs(v.x - p.x) < 8)
          if (near >= 0) { setSelected(near); return }
          if (points.length >= 16 || p.x === 0 || p.x === 255) return
          const next = [...points, p].sort((a,b) => a.x - b.x)
          const i = next.indexOf(p)
          setSelected(i); drag.current = i
          event.currentTarget.setPointerCapture(event.pointerId)
          onChange({ ...value, [channel]: { points: next } })
        }}
        onPointerMove={event => { if (!disabled && drag.current !== null) { const p = position(event); update(drag.current, p.x, p.y) } }}
        onPointerUp={() => { drag.current = null; onCommit() }} onPointerCancel={() => { drag.current = null; onCommit() }}
        onLostPointerCapture={() => { drag.current = null }}>
        <svg viewBox="0 0 255 255" aria-hidden="true">
          {[64,128,192].map(n => <path key={n} className={styles.grid} d={`M${n} 0V255 M0 ${n}H255`}/>)}
          <path className={styles.diagonal} d="M0 255L255 0"/>
          {CHANNELS.filter(key => key !== channel && value[key].points.some(p => p.x !== p.y)).map(key =>
            <path key={key} opacity=".25" stroke={COLORS[key]} d={Array.from({length:256}, (_,x) => `${x ? 'L' : 'M'}${x} ${255-curveValue(value[key].points,x)}`).join(' ')}/>)}
          <path stroke={COLORS[channel]} strokeWidth="2" d={Array.from({length:256}, (_,x) => `${x ? 'L' : 'M'}${x} ${255-curveValue(points,x)}`).join(' ')}/>
        </svg>
        {points.map((p,i) => <button type="button" key={i} className={`${styles.point} ${index === i ? styles.selected : ''}`}
          style={{left:`${p.x/255*100}%`, top:`${(255-p.y)/255*100}%`}} aria-label={`${LABELS[channel]} point ${i+1}: input ${p.x}, output ${p.y}`} aria-describedby={`${id}-help`}
          onFocus={() => setSelected(i)} onPointerDown={event => { if (event.button !== 0) return; event.stopPropagation(); setSelected(i); drag.current = i; graph.current!.setPointerCapture(event.pointerId) }}
          onKeyDown={event => {
            if (['Delete','Backspace'].includes(event.key)) { event.preventDefault(); remove(i); return }
            const step = event.shiftKey ? 10 : 1
            const delta = { ArrowLeft: [-step,0], ArrowRight:[step,0], ArrowUp:[0,step], ArrowDown:[0,-step] }[event.key]
            if (delta) { event.preventDefault(); update(i,p.x+delta[0],p.y+delta[1]) }
          }} onKeyUp={onCommit}/>) }
      </div>
      <div className={styles.axis}><span>Shadows</span><span>Highlights</span></div>
      <div className={styles.coordinates}>
        <label>Input<input type="number" min={index === 0 ? 0 : points[index-1].x+1} max={index === points.length-1 ? 255 : points[index+1].x-1} value={point.x} disabled={disabled || index === 0 || index === points.length-1}
          onChange={e => { if (e.target.value !== '') update(index,Number(e.target.value),point.y) }} onBlur={onCommit}/></label>
        <label>Output<input type="number" min="0" max="255" value={point.y} onChange={e => { if (e.target.value !== '') update(index,point.x,Number(e.target.value)) }} onBlur={onCommit}/></label>
      </div>
      <div className={styles.actions}><button type="button" disabled={disabled || points.length >= 16} onClick={addPoint}>Add point</button><button type="button" disabled={disabled || index === 0 || index === points.length-1} onClick={() => remove(index)}>Remove point</button>
        <button type="button" aria-label={`Reset ${LABELS[channel]} curve`} onClick={() => { onChange({...value,[channel]:identityCurves()[channel]}); setSelected(0) }}><RotateCcw size={12}/>Reset {LABELS[channel]}</button></div>
    </fieldset>
  </details>
}
