import { useEffect, useRef, useState, type CSSProperties, type DragEvent } from 'react'
import { Link } from '@tanstack/react-router'
import { ArrowLeft, ArrowUpRight, Check, ChevronRight, Download, ImagePlus, Info, Layers, LoaderCircle, Maximize2, RotateCcw, ScanLine, ShieldCheck, SlidersHorizontal, Sparkles, Upload, X } from 'lucide-react'
import { Brand } from '../components/Brand'
import { PhotoPreview } from '../components/PhotoPreview'
import { CONTROL_GROUPS, loadPhoto, NEUTRAL, PRESETS, type Adjustments, type LocalPhoto } from '../lib/editor'
import styles from './Studio.module.css'

export function Studio() {
  const [photo, setPhoto] = useState<LocalPhoto | null>(null)
  const [values, setValues] = useState<Adjustments>({ ...NEUTRAL })
  const [activePreset, setActivePreset] = useState('Original')
  const [compare, setCompare] = useState(false)
  const [split, setSplit] = useState(50)
  const [panel, setPanel] = useState<'presets' | 'adjustments'>('adjustments')
  const [loading, setLoading] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const [modal, setModal] = useState<'enhance' | 'export' | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const dialog = useRef<HTMLDialogElement>(null)
  const requestId = useRef(0)
  const currentPhoto = useRef<LocalPhoto | null>(null)
  const lastTrigger = useRef<HTMLElement | null>(null)

  useEffect(() => () => { requestId.current++; if (currentPhoto.current?.local) URL.revokeObjectURL(currentPhoto.current.url) }, [])
  useEffect(() => {
    if (modal) { lastTrigger.current = document.activeElement as HTMLElement; dialog.current?.showModal() }
    else { dialog.current?.close(); lastTrigger.current?.focus(); lastTrigger.current = null }
  }, [modal])
  useEffect(() => { document.title = 'Editing Studio — LumaLab'; return () => { document.title = 'LumaLab — Light. Colour. Create.' } }, [])

  function reset() { setValues({ ...NEUTRAL }); setActivePreset('Original'); setStatus('All adjustments reset to Original.') }
  function commit(next: LocalPhoto) {
    if (currentPhoto.current?.local) URL.revokeObjectURL(currentPhoto.current.url)
    currentPhoto.current = next
    setPhoto(next); setValues({ ...NEUTRAL }); setActivePreset('Original'); setCompare(false); setSplit(50)
    setStatus(`${next.name} is ready to edit.`)
  }
  async function upload(file: File) {
    const id = ++requestId.current
    setLoading(true); setError(''); setStatus('Reading your photograph…')
    try {
      const next = await loadPhoto(file)
      if (id !== requestId.current) { URL.revokeObjectURL(next.url); return }
      commit(next)
    } catch (caught) { if (id === requestId.current) { setError(caught instanceof Error ? caught.message : 'Unable to read this photograph. Choose another image.'); setStatus('') } }
    finally { if (id === requestId.current) setLoading(false) }
  }
  async function useSample() {
    const id = ++requestId.current
    setLoading(true); setError('')
    try {
      const image = new Image(); image.src = '/images/alpine.jpg'; await image.decode()
      if (id === requestId.current) commit({ url: image.src, name: 'alpine-perspective.jpg', width: image.naturalWidth, height: image.naturalHeight, format: 'JPEG', local: false })
    } catch { if (id === requestId.current) setError('The sample could not be loaded. Try choosing your own photograph.') }
    finally { if (id === requestId.current) setLoading(false) }
  }
  function drop(event: DragEvent) {
    event.preventDefault(); setDragging(false)
    if (event.dataTransfer.files.length !== 1) { setError('Choose one photograph at a time.'); return }
    void upload(event.dataTransfer.files[0])
  }
  const dirty = Object.entries(values).some(([key,value]) => value !== NEUTRAL[key as keyof Adjustments])

  return <div className={styles.studio}>
    <header className={styles.header}><Brand /><div className={styles.breadcrumb}><ChevronRight size={12} /><span>Editing Studio</span><span className={styles.version}>V.01</span></div><div className={styles.headerActions}><Link to="/" className={styles.backLink}><ArrowLeft size={14} /> Back to home</Link><button className="button primary" disabled={!photo || loading} onClick={() => setModal('export')}><Download size={15} /><span>Export image</span></button></div></header>
    <div className={styles.previewNotice}><Info size={13} /><span>Frontend preview <i>—</i> Explore with a local photograph. Auto Enhance and export are awaiting the editing service.</span><span className={styles.localBadge}><span className="status-dot" /> LOCAL PREVIEW</span></div>
    <input ref={fileInput} type="file" className="sr-only" tabIndex={-1} aria-label="Photograph file" accept=".jpg,.jpeg,.png,.webp" onChange={e => { const file = e.target.files?.[0]; if (file) void upload(file); e.target.value = '' }} />
    <main id="main" className={styles.workspace}>
      <aside className={`${styles.leftPanel} ${panel === 'presets' ? styles.mobileVisible : ''}`} aria-label="Upload and presets">
        <div className={styles.panelTitle}><Layers size={15}/><h2>Your toolkit</h2><span>01</span></div>
        <div className={styles.uploadSection}><span className={styles.label}>YOUR PHOTOGRAPH</span><button className={styles.uploadButton} onClick={() => fileInput.current?.click()} disabled={loading}><Upload size={17}/>{photo ? 'Replace photograph' : 'Upload photograph'}<span>+</span></button><p>JPG, PNG or WebP · Up to 10 MB<br/>24 MP · 10,000 px per side</p></div>
        <div className={styles.presetSection}><div className={styles.sectionLabel}><span className={styles.label}>PRESET LIBRARY</span><span>05</span></div><p>A starting point for your perspective.</p><div className={styles.presetList}>{PRESETS.map((preset,index) => <button key={preset.name} disabled={!photo} aria-pressed={activePreset === preset.name} className={`${styles.preset} ${activePreset === preset.name && photo ? styles.activePreset : ''}`} onClick={() => { setValues({ ...preset.values }); setActivePreset(preset.name); setStatus(`${preset.name} preset applied.`) }}><img src={photo?.url || '/images/alpine.jpg'} alt="" style={{filter:`saturate(${preset.values.saturation / 100}) contrast(${preset.values.contrast / 100}) sepia(${preset.values.warmth > 0 ? .35 : 0})`}}/><span><strong>{preset.name}</strong><small>{preset.description}</small></span>{activePreset === preset.name && photo ? <Check size={14}/> : <span className={styles.presetNumber}>0{index+1}</span>}</button>)}</div></div>
        <div className={styles.enhanceSection}><div><Sparkles size={17}/><span>A little assistance</span></div><p>A balanced starting point, with you in control.</p><button className="button secondary" disabled={!photo || loading} onClick={() => setModal('enhance')}><Sparkles size={14}/>Auto Enhance<ArrowUpRight size={14}/></button><span className={styles.coming}>EDITING SERVICE REQUIRED</span></div>
        <div className={styles.preserveNote}><ShieldCheck size={14}/><span>Your original stays untouched.</span></div>
      </aside>

      <section className={styles.center} aria-label="Photograph workspace">
        <div className={styles.workspaceToolbar}><div><span className="status-dot"/><h1>{photo ? 'Your perspective' : 'A fresh perspective'}</h1></div><span className={styles.workspaceMode}>{photo ? activePreset.toUpperCase() : 'READY WHEN YOU ARE'}</span></div>
        <div className={`${styles.canvas} ${dragging ? styles.dragging : ''}`} onDragOver={e => { e.preventDefault(); setDragging(true) }} onDragLeave={e => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragging(false) }} onDrop={drop}>
          {photo ? <><div className={styles.imageContainer} style={{ '--photo-ratio': photo.width / photo.height } as CSSProperties}><PhotoPreview src={photo.url} name={photo.name} values={values} compare={compare} split={split} onSplit={setSplit} eager/></div>{loading && <div className={styles.loadingOverlay}><LoaderCircle className={styles.spinner} size={22}/><span>Reading photograph…</span></div>}</> : <div className={styles.emptyState}><div className={styles.emptyIcon}><ImagePlus size={34} strokeWidth={1}/><span>+</span></div><span className="eyebrow">EVERY EDIT STARTS WITH A MOMENT</span><h2>Bring your photograph<br/>into the light.</h2><p>Drop a photograph here, or choose one from your device.<br/>A little perspective goes a long way.</p><button className="button primary" onClick={() => fileInput.current?.click()} disabled={loading}>{loading ? <LoaderCircle className={styles.spinner} size={17}/> : <Upload size={16}/>} {loading ? 'Reading photograph…' : 'Choose a photograph'}</button><span className={styles.uploadLimits}>JPG, PNG, WEBP · MAX 10 MB · 24 MP</span><div className={styles.sampleDivider}><span/>OR EXPLORE FIRST<span/></div><button className={styles.sampleButton} onClick={() => void useSample()} disabled={loading}><img src="/images/alpine.jpg" alt="" width="47" height="36"/><span>Try a sample photograph<small>A view worth a second look.</small></span><ArrowUpRight size={16}/></button></div>}
          {dragging && <div className={styles.dropOverlay}><Upload size={28}/><span>Drop one photograph to begin</span></div>}
        </div>
        <div className={styles.workspaceBottom}><div className={styles.imageInfo}>{photo ? <><span title={photo.name}>{photo.name}</span><small>{photo.width} × {photo.height} <i>·</i> {photo.format}</small></> : <><span>No photograph selected</span><small>Your creative space is ready.</small></>}</div><span className={styles.fitLabel}><Maximize2 size={13}/>Fit</span><button className={compare ? styles.compareActive : ''} disabled={!photo} aria-pressed={compare} onClick={() => setCompare(!compare)}><ScanLine size={15}/><span>Compare</span></button></div>
        {error && <div role="alert" className={styles.error}><Info size={16}/><span>{error}</span><button aria-label="Dismiss error" onClick={() => setError('')}><X size={15}/></button></div>}
        <div role="status" className={styles.status}>{status || 'Your photograph stays in this browser during the frontend preview.'}</div>
      </section>

      <div className={styles.mobileTabs} role="group" aria-label="Editing panels"><button aria-pressed={panel === 'presets'} onClick={() => setPanel('presets')}><Layers size={16}/>Presets & upload</button><button aria-pressed={panel === 'adjustments'} onClick={() => setPanel('adjustments')}><SlidersHorizontal size={16}/>Adjustments</button></div>

      <aside className={`${styles.rightPanel} ${panel === 'adjustments' ? styles.mobileVisible : ''}`} aria-label="Image adjustments"><div className={styles.panelTitle}><SlidersHorizontal size={15}/><h2>Adjustments</h2><button onClick={reset} disabled={!photo || !dirty} aria-label="Reset all adjustments" title="Reset all adjustments"><RotateCcw size={14}/></button></div><div className={styles.adjustmentHeader}><span className={styles.label}>MAKE IT YOURS</span><span>{photo ? activePreset : 'Original'}</span></div>
        {CONTROL_GROUPS.map(group => <fieldset key={group.name} className={styles.controlGroup} disabled={!photo}><legend><span style={{background:group.color}}/>{group.name}</legend>{group.controls.map(control => <div className={styles.control} key={control.key}><div><label htmlFor={control.key}>{control.label}</label><output htmlFor={control.key}>{control.key === 'warmth' && values[control.key] > 0 ? '+' : ''}{values[control.key]}</output></div><input id={control.key} type="range" min={control.min} max={control.max} step="1" value={values[control.key]} style={{ '--control-color': group.color, '--range-progress': `${(values[control.key]-control.min)/(control.max-control.min)*100}%` } as CSSProperties} onChange={e => { setValues(current => ({ ...current, [control.key]: Number(e.target.value) })); setActivePreset('Custom'); setStatus('Local preview updated.') }}/><div className={styles.rangeLabels}><span>{control.min}</span><span>{control.max > 0 && control.min < 0 ? '+' : ''}{control.max}</span></div></div>)}</fieldset>)}
        <div className={styles.resetSection}><button className="button secondary" onClick={reset} disabled={!photo || !dirty}><RotateCcw size={13}/>Reset adjustments</button><p>Every adjustment starts from your original.</p></div>
      </aside>
    </main>
    <footer className={styles.studioFooter}><span><span className="status-dot"/> LUMALAB / CREATIVE WORKSPACE</span><span>LIGHT. COLOUR. CREATE.</span><span>ONE ORIGINAL. YOUR PERSPECTIVE.</span></footer>
    <dialog ref={dialog} className={styles.dialog} onCancel={() => setModal(null)} onClose={() => setModal(null)} onClick={e => { if (e.target === e.currentTarget) { const r=e.currentTarget.getBoundingClientRect(); if(e.clientX<r.left || e.clientX>r.right || e.clientY<r.top || e.clientY>r.bottom) setModal(null) } }} aria-labelledby="dialog-title" aria-describedby="dialog-description"><div className={styles.dialogTop}><span className="eyebrow">{modal === 'export' ? 'THE FINAL FRAME' : 'A LITTLE ASSISTANCE'}</span><button className="icon-button" aria-label="Close dialog" onClick={() => setModal(null)}><X size={18}/></button></div><div className={styles.dialogIcon}>{modal === 'export' ? <Download size={27}/> : <Sparkles size={27}/>}</div><h2 id="dialog-title">{modal === 'export' ? 'Your photograph, ready for the world.' : 'A balanced starting point.'}</h2><p id="dialog-description">{modal === 'export' ? 'Full-resolution downloads will be available when the editing service is connected. Your current adjustments are kept while you explore.' : 'Auto Enhance will analyse your original photograph to balance brightness, contrast, saturation and warmth. This feature needs the editing service, which is not connected yet.'}</p>{modal === 'export' && <><dl className={styles.exportDetails}><div><dt>Format</dt><dd>JPEG</dd></div><div><dt>Quality</dt><dd>92 / 100</dd></div><div><dt>Resolution</dt><dd>{photo?.width} × {photo?.height}</dd></div><div><dt>Look</dt><dd>{activePreset}</dd></div></dl><p className={styles.exportNote}>Planned export: transparent areas become white, with sRGB colour and EXIF/GPS metadata removed. These guarantees require backend processing.</p></>}<div className={styles.serviceNote}><Info size={15}/><span>Editing service not connected</span></div><button className="button primary" onClick={() => setModal(null)}>Keep creating <ArrowUpRight size={16}/></button></dialog>
  </div>
}
