import { useEffect, useRef, useState, type CSSProperties, type DragEvent } from 'react'
import { Link } from '@tanstack/react-router'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ArrowLeft, ArrowUpRight, Check, ChevronRight, Download, ImagePlus, Info, Layers, LoaderCircle, Maximize2, RotateCcw, ScanLine, ShieldCheck, SlidersHorizontal, Sparkles, Upload, X } from 'lucide-react'
import { Brand } from '../components/Brand'
import { PhotoPreview } from '../components/PhotoPreview'
import { CONTROL_GROUPS, loadPhoto, NEUTRAL, type Adjustments, type LocalPhoto } from '../lib/editor'
import { ApiError, deleteImage, enhanceImage, exportImage, getOriginalPreview, getPresets, getPreview, uploadImage } from '../lib/api'
import styles from './Studio.module.css'

type StudioPhoto = LocalPhoto & {
  imageId: string
  accessToken: string
  expiresAt: string
  originalPreviewUrl: string
  previewUrl: string
}

function errorMessage(caught: unknown, fallback: string): string {
  if (caught instanceof ApiError) {
    if (caught.status === 410 || caught.code === 'image_expired') return 'This image session expired. Upload the photograph again to continue.'
    if (caught.status === 503 || caught.code === 'service_unavailable') return 'The editing service is temporarily unavailable. Try again shortly.'
    return caught.message
  }
  if (caught instanceof TypeError) return 'Could not complete the request. Check your connection and try again.'
  return caught instanceof Error ? caught.message : fallback
}

export function Studio() {
  const presetsQuery = useQuery({
    queryKey: ['presets'],
    queryFn: ({ signal }) => getPresets(signal),
    staleTime: 5 * 60 * 1000,
  })
  const uploadMutation = useMutation({ mutationFn: ({ file, signal }: { file: File; signal: AbortSignal }) => uploadImage(file, signal), gcTime: 0 })
  const enhancementMutation = useMutation({ mutationFn: ({ imageId, token, signal }: { imageId: string; token: string; signal: AbortSignal }) => enhanceImage(imageId, token, signal), gcTime: 0 })
  const exportMutation = useMutation({ mutationFn: ({ imageId, token, adjustments, signal }: { imageId: string; token: string; adjustments: Adjustments; signal: AbortSignal }) => exportImage(imageId, token, adjustments, signal), gcTime: 0 })
  const deleteMutation = useMutation({ mutationFn: ({ imageId, token }: { imageId: string; token: string }) => deleteImage(imageId, token), gcTime: 0 })
  const [photo, setPhoto] = useState<StudioPhoto | null>(null)
  const [values, setValues] = useState<Adjustments>({ ...NEUTRAL })
  const [activePreset, setActivePreset] = useState('Original')
  const [compare, setCompare] = useState(false)
  const [split, setSplit] = useState(50)
  const [previewReady, setPreviewReady] = useState(false)
  const [previewFlush, setPreviewFlush] = useState(0)
  const [panel, setPanel] = useState<'presets' | 'adjustments'>('adjustments')
  const [loading, setLoading] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const [modal, setModal] = useState<'enhance' | 'export' | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const dialog = useRef<HTMLDialogElement>(null)
  const requestId = useRef(0)
  const currentPhoto = useRef<StudioPhoto | null>(null)
  const previewController = useRef<AbortController | null>(null)
  const uploadController = useRef<AbortController | null>(null)
  const enhancementController = useRef<AbortController | null>(null)
  const exportController = useRef<AbortController | null>(null)
  const previewRevision = useRef(0)
  const editRevision = useRef(0)
  const previewNow = useRef(false)
  const activePreviewKey = useRef('')
  const renderedPreviewKey = useRef('')
  const enhancementFeedback = useRef('')
  const lastTrigger = useRef<HTMLElement | null>(null)

  function resetImageMutationState() {
    uploadMutation.reset()
    enhancementMutation.reset()
    exportMutation.reset()
    deleteMutation.reset()
  }

  useEffect(() => () => {
    requestId.current++
    uploadController.current?.abort()
    previewController.current?.abort()
    enhancementController.current?.abort()
    exportController.current?.abort()
    const current = currentPhoto.current
    if (current) {
      if (current.previewUrl !== current.originalPreviewUrl) URL.revokeObjectURL(current.previewUrl)
      URL.revokeObjectURL(current.originalPreviewUrl)
      void deleteImage(current.imageId, current.accessToken).catch(() => {})
    }
    resetImageMutationState()
  }, [])
  useEffect(() => {
    if (modal) { lastTrigger.current ??= document.activeElement as HTMLElement; dialog.current?.showModal() }
    else { dialog.current?.close(); lastTrigger.current?.focus(); lastTrigger.current = null }
  }, [modal])
  useEffect(() => { document.title = 'Editing Studio — LumaLab'; return () => { document.title = 'LumaLab — Light. Colour. Create.' } }, [])

  useEffect(() => {
    if (!photo) return
    const requestKey = `${photo.imageId}:${JSON.stringify(values)}`
    const immediate = previewNow.current
    previewNow.current = false
    const isNeutral = Object.entries(values).every(([key, value]) => value === NEUTRAL[key as keyof Adjustments])
    if (isNeutral) {
      renderedPreviewKey.current = requestKey
      const current = currentPhoto.current
      if (current?.imageId === photo.imageId && current.previewUrl !== current.originalPreviewUrl) {
        URL.revokeObjectURL(current.previewUrl)
        const next = { ...current, previewUrl: current.originalPreviewUrl, url: current.originalPreviewUrl }
        currentPhoto.current = next
        setPhoto(next)
      }
      setPreviewReady(true)
      if (!enhancementFeedback.current) setStatus('Original preview is ready.')
      return
    }
    if (renderedPreviewKey.current === requestKey) {
      setPreviewReady(true)
      return
    }
    previewController.current?.abort()
    const controller = new AbortController()
    previewController.current = controller
    const revision = ++previewRevision.current
    setPreviewReady(false)
    if (!enhancementFeedback.current) setStatus('Updating the image preview…')
    const timer = window.setTimeout(async () => {
      activePreviewKey.current = requestKey
      try {
        const result = await getPreview(photo.imageId, photo.accessToken, revision, values, controller.signal)
        if (controller.signal.aborted || currentPhoto.current?.imageId !== photo.imageId || previewRevision.current !== revision) return
        if (result.revision !== String(revision)) throw new Error('The preview response did not match the latest settings. Try again.')
        const current = currentPhoto.current
        if (!current || current.imageId !== photo.imageId) return
        const previewUrl = URL.createObjectURL(result.blob)
        if (current.previewUrl !== current.originalPreviewUrl) URL.revokeObjectURL(current.previewUrl)
        const next = { ...current, previewUrl, url: previewUrl }
        currentPhoto.current = next
        renderedPreviewKey.current = requestKey
        setPhoto(next)
        setPreviewReady(true)
        setError('')
        setStatus(enhancementFeedback.current || 'Preview is up to date.')
      } catch (caught) {
        if (controller.signal.aborted || (caught instanceof Error && caught.name === 'AbortError')) return
        if (currentPhoto.current?.imageId === photo.imageId && previewRevision.current === revision) {
          setError(errorMessage(caught, 'Unable to update the preview.'))
          setPreviewReady(false)
          setStatus('The last successful preview is still available; the current settings were not rendered.')
        }
      } finally {
        if (activePreviewKey.current === requestKey) activePreviewKey.current = ''
      }
    }, immediate ? 0 : 250)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
      if (activePreviewKey.current === requestKey) activePreviewKey.current = ''
    }
  }, [photo?.imageId, photo?.accessToken, values, previewFlush])

  function flushPreview() {
    const current = currentPhoto.current
    if (!current) return
    const requestKey = `${current.imageId}:${JSON.stringify(values)}`
    if (activePreviewKey.current === requestKey || renderedPreviewKey.current === requestKey) return
    previewNow.current = true
    setPreviewFlush(current => current + 1)
  }

  function invalidatePreview() {
    previewRevision.current++
    previewController.current?.abort()
  }
  function invalidateEnhancement() {
    editRevision.current++
    enhancementController.current?.abort()
  }
  function invalidateEditedWork() {
    invalidatePreview()
    invalidateEnhancement()
  }
  function reset() { invalidateEditedWork(); enhancementFeedback.current = ''; setValues({ ...NEUTRAL }); setActivePreset('Original'); setStatus('All adjustments reset to Original.') }
  function releasePhoto(current: StudioPhoto) {
    if (current.previewUrl !== current.originalPreviewUrl) URL.revokeObjectURL(current.previewUrl)
    URL.revokeObjectURL(current.originalPreviewUrl)
    void deleteMutation.mutateAsync({ imageId: current.imageId, token: current.accessToken }).catch(() => {}).finally(() => deleteMutation.reset())
  }
  function cancelImageWork() {
    invalidateEditedWork()
    exportController.current?.abort()
  }
  function commit(next: StudioPhoto) {
    cancelImageWork()
    resetImageMutationState()
    const previous = currentPhoto.current
    if (previous) releasePhoto(previous)
    currentPhoto.current = next
    enhancementFeedback.current = ''
    setPreviewReady(true)
    setPhoto(next); setValues({ ...NEUTRAL }); setActivePreset('Original'); setCompare(false); setSplit(50)
    setStatus(`${next.name} is ready to edit.`)
  }
  async function upload(file: File) {
    const id = ++requestId.current
    uploadController.current?.abort()
    invalidateEnhancement()
    exportController.current?.abort()
    setLoading(true); setError(''); setStatus('Reading your photograph…')
    const controller = new AbortController()
    uploadController.current = controller
    let local: LocalPhoto | null = null
    let session: Awaited<ReturnType<typeof uploadImage>> | null = null
    try {
      local = await loadPhoto(file)
      if (id !== requestId.current) return
      setStatus('Uploading and preparing your photograph…')
      session = await uploadMutation.mutateAsync({ file, signal: controller.signal })
      const originalBlob = await getOriginalPreview(session.image_id, session.access_token, controller.signal)
      if (id !== requestId.current) {
        void deleteImage(session.image_id, session.access_token).catch(() => {})
        return
      }
      const originalPreviewUrl = URL.createObjectURL(originalBlob)
      const next: StudioPhoto = {
        ...local,
        url: originalPreviewUrl,
        name: session.filename,
        format: session.format,
        width: session.width,
        height: session.height,
        local: false,
        imageId: session.image_id,
        accessToken: session.access_token,
        expiresAt: session.expires_at,
        originalPreviewUrl,
        previewUrl: originalPreviewUrl,
      }
      commit(next)
      URL.revokeObjectURL(local.url)
      local = null
      session = null
    } catch (caught) {
      if (session) void deleteImage(session.image_id, session.access_token).catch(() => {})
      if (id === requestId.current) {
        setError(errorMessage(caught, 'Unable to upload this photograph. Try again.'))
        setStatus('Your current photograph and edits were kept.')
      }
    } finally {
      if (local) URL.revokeObjectURL(local.url)
      if (id === requestId.current) setLoading(false)
      uploadMutation.reset()
    }
  }
  async function useSample() {
    try {
      const response = await fetch('/images/alpine.jpg')
      if (!response.ok) throw new Error('The sample could not be loaded. Try choosing your own photograph.')
      const file = new File([await response.blob()], 'alpine-perspective.jpg', { type: 'image/jpeg' })
      await upload(file)
    } catch (caught) {
      setError(errorMessage(caught, 'The sample could not be loaded. Try choosing your own photograph.'))
    }
  }
  async function autoEnhance() {
    const target = currentPhoto.current
    if (!target || enhancementMutation.isPending) return
    enhancementController.current?.abort()
    const controller = new AbortController()
    enhancementController.current = controller
    const revisionAtStart = editRevision.current
    enhancementFeedback.current = ''
    setError(''); setStatus('Analyzing your original photograph…')
    try {
      const result = await enhancementMutation.mutateAsync({ imageId: target.imageId, token: target.accessToken, signal: controller.signal })
      if (controller.signal.aborted || editRevision.current !== revisionAtStart || currentPhoto.current?.imageId !== target.imageId) return
      invalidatePreview()
      setValues({ ...result.adjustments })
      setPreviewReady(false)
      enhancementFeedback.current = result.message
      setActivePreset('Auto Enhanced')
      setStatus(result.message)
      setModal(null)
    } catch (caught) {
      if (controller.signal.aborted || (caught instanceof Error && caught.name === 'AbortError')) return
      if (currentPhoto.current?.imageId === target.imageId) {
        setError(errorMessage(caught, 'Auto Enhance could not finish. Try again.'))
        setStatus('Your previous adjustments were kept.')
      }
    } finally {
      enhancementMutation.reset()
    }
  }
  async function downloadExport() {
    const target = currentPhoto.current
    if (!target || !previewReady || exportMutation.isPending) return
    const snapshot = { ...values }
    exportController.current?.abort()
    const controller = new AbortController()
    exportController.current = controller
    setError(''); setStatus('Preparing your full-resolution JPEG…')
    try {
      const result = await exportMutation.mutateAsync({ imageId: target.imageId, token: target.accessToken, adjustments: snapshot, signal: controller.signal })
      if (controller.signal.aborted || currentPhoto.current?.imageId !== target.imageId) return
      const url = URL.createObjectURL(result.blob)
      const headerName = result.contentDisposition?.match(/filename="([^"]+)"/i)?.[1]
      const filename = headerName?.replace(/[^A-Za-z0-9._-]/g, '') || 'lumalab-image.jpg'
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      link.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
      setModal(null)
      setStatus('Your JPEG export is ready.')
    } catch (caught) {
      if (controller.signal.aborted || (caught instanceof Error && caught.name === 'AbortError')) return
      if (currentPhoto.current?.imageId === target.imageId) {
        setError(errorMessage(caught, 'The export could not be prepared. Try again.'))
        setStatus('Your current adjustments were kept.')
      }
    } finally {
      exportMutation.reset()
    }
  }
  function drop(event: DragEvent) {
    event.preventDefault(); setDragging(false)
    if (event.dataTransfer.files.length !== 1) { setError('Choose one photograph at a time.'); return }
    void upload(event.dataTransfer.files[0])
  }
  const dirty = Object.entries(values).some(([key,value]) => value !== NEUTRAL[key as keyof Adjustments])

  return <div className={styles.studio}>
    <header className={styles.header}><Brand /><div className={styles.breadcrumb}><ChevronRight size={12} /><span>Editing Studio</span><span className={styles.version}>V.01</span></div><div className={styles.headerActions}><Link to="/" className={styles.backLink}><ArrowLeft size={14} /> Back to home</Link><button className="button primary" disabled={!photo || loading || !previewReady || exportMutation.isPending} onClick={event => { lastTrigger.current = event.currentTarget; setModal('export') }}><Download size={15} /><span>{exportMutation.isPending ? 'Exporting…' : 'Export image'}</span></button></div></header>
    <div className={styles.previewNotice}><Info size={13} /><span>Your photograph is uploaded securely for editing and export. The original remains untouched.</span><span className={styles.localBadge}><span className="status-dot" /> PRIVATE SESSION</span></div>
    <input ref={fileInput} type="file" className="sr-only" tabIndex={-1} aria-label="Photograph file" accept=".jpg,.jpeg,.png,.webp" onChange={e => { const file = e.target.files?.[0]; if (file) void upload(file); e.target.value = '' }} />
    <main id="main" className={styles.workspace}>
      <aside className={`${styles.leftPanel} ${panel === 'presets' ? styles.mobileVisible : ''}`} aria-label="Upload and presets">
        <div className={styles.panelTitle}><Layers size={15}/><h2>Your toolkit</h2><span>01</span></div>
        <div className={styles.uploadSection}><span className={styles.label}>YOUR PHOTOGRAPH</span><button className={styles.uploadButton} onClick={() => fileInput.current?.click()} disabled={loading}><Upload size={17}/>{photo ? 'Replace photograph' : 'Upload photograph'}<span>+</span></button><p>JPG, PNG or WebP · Up to 10 MB<br/>24 MP · 10,000 px per side</p></div>
        <div className={styles.presetSection}><div className={styles.sectionLabel}><span className={styles.label}>PRESET LIBRARY</span><span>{String(presetsQuery.data?.length ?? 0).padStart(2, '0')}</span></div><p>A starting point for your perspective.</p>{presetsQuery.isPending && <p role="status">Loading presets…</p>}{presetsQuery.isError && <p role="alert">Presets are temporarily unavailable.</p>}<div className={styles.presetList}>{presetsQuery.data?.map((preset,index) => {
          const presetValues: Adjustments = {
            brightness: preset.brightness,
            contrast: preset.contrast,
            saturation: preset.saturation,
            warmth: preset.warmth,
            sharpness: preset.sharpness,
            vignette: preset.vignette,
          }
          return <button key={preset.preset_id} disabled={!photo} aria-pressed={activePreset === preset.preset_name} className={`${styles.preset} ${activePreset === preset.preset_name && photo ? styles.activePreset : ''}`} onClick={() => { invalidateEditedWork(); enhancementFeedback.current = ''; setPreviewReady(false); setValues(presetValues); setActivePreset(preset.preset_name); setStatus(`${preset.preset_name} preset applied.`) }}><img src={photo?.previewUrl || '/images/alpine.jpg'} alt="" style={{filter:`saturate(${preset.saturation / 100}) contrast(${preset.contrast / 100}) sepia(${preset.warmth > 0 ? .35 : 0})`}}/><span><strong>{preset.preset_name}</strong><small>{preset.description}</small></span>{activePreset === preset.preset_name && photo ? <Check size={14}/> : <span className={styles.presetNumber}>0{index+1}</span>}</button>
        })}</div></div>
        <div className={styles.enhanceSection}><div><Sparkles size={17}/><span>A little assistance</span></div><p>A balanced starting point, with you in control.</p><button className="button secondary" disabled={!photo || loading || enhancementMutation.isPending} onClick={event => { lastTrigger.current = event.currentTarget; setModal('enhance') }}><Sparkles size={14}/>{enhancementMutation.isPending ? 'Analyzing…' : 'Auto Enhance'}<ArrowUpRight size={14}/></button></div>
        <div className={styles.preserveNote}><ShieldCheck size={14}/><span>Your original stays untouched.</span></div>
      </aside>

      <section className={styles.center} aria-label="Photograph workspace">
        <div className={styles.workspaceToolbar}><div><span className="status-dot"/><h1>{photo ? 'Your perspective' : 'A fresh perspective'}</h1></div><span className={styles.workspaceMode}>{photo ? (previewReady ? activePreset.toUpperCase() : 'PREVIEW OUTDATED') : 'READY WHEN YOU ARE'}</span></div>
        <div className={`${styles.canvas} ${dragging ? styles.dragging : ''}`} onDragOver={e => { e.preventDefault(); setDragging(true) }} onDragLeave={e => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragging(false) }} onDrop={drop}>
          {photo ? <><div className={styles.imageContainer} style={{ '--photo-ratio': photo.width / photo.height } as CSSProperties}><PhotoPreview src={photo.previewUrl} originalSrc={photo.originalPreviewUrl} name={photo.name} values={values} compare={compare} split={split} onSplit={setSplit} authoritative eager/></div>{loading && <div className={styles.loadingOverlay}><LoaderCircle className={styles.spinner} size={22}/><span>Uploading photograph…</span></div>}</> : <div className={styles.emptyState}><div className={styles.emptyIcon}><ImagePlus size={34} strokeWidth={1}/><span>+</span></div><span className="eyebrow">EVERY EDIT STARTS WITH A MOMENT</span><h2>Bring your photograph<br/>into the light.</h2><p>Drop a photograph here, or choose one from your device.<br/>A little perspective goes a long way.</p><button className="button primary" onClick={() => fileInput.current?.click()} disabled={loading}>{loading ? <LoaderCircle className={styles.spinner} size={17}/> : <Upload size={16}/>} {loading ? 'Uploading photograph…' : 'Choose a photograph'}</button><span className={styles.uploadLimits}>JPG, PNG, WEBP · MAX 10 MB · 24 MP</span><div className={styles.sampleDivider}><span/>OR EXPLORE FIRST<span/></div><button className={styles.sampleButton} onClick={() => void useSample()} disabled={loading}><img src="/images/alpine.jpg" alt="" width="47" height="36"/><span>Try a sample photograph<small>A view worth a second look.</small></span><ArrowUpRight size={16}/></button></div>}
          {dragging && <div className={styles.dropOverlay}><Upload size={28}/><span>Drop one photograph to begin</span></div>}
        </div>
        <div className={styles.workspaceBottom}><div className={styles.imageInfo}>{photo ? <><span title={photo.name}>{photo.name}</span><small>{photo.width} × {photo.height} <i>·</i> {photo.format}</small></> : <><span>No photograph selected</span><small>Your creative space is ready.</small></>}</div><span className={styles.fitLabel}><Maximize2 size={13}/>Fit</span><button className={compare ? styles.compareActive : ''} disabled={!photo} aria-pressed={compare} onClick={() => setCompare(!compare)}><ScanLine size={15}/><span>Compare</span></button></div>
        {error && <div role="alert" className={styles.error}><Info size={16}/><span>{error}</span><button aria-label="Dismiss error" onClick={() => setError('')}><X size={15}/></button></div>}
        <div role="status" className={styles.status}>{status || 'Your original stays untouched while previews are rendered from its normalized copy.'}</div>
      </section>

      <div className={styles.mobileTabs} role="group" aria-label="Editing panels"><button aria-pressed={panel === 'presets'} onClick={() => setPanel('presets')}><Layers size={16}/>Presets & upload</button><button aria-pressed={panel === 'adjustments'} onClick={() => setPanel('adjustments')}><SlidersHorizontal size={16}/>Adjustments</button></div>

      <aside className={`${styles.rightPanel} ${panel === 'adjustments' ? styles.mobileVisible : ''}`} aria-label="Image adjustments"><div className={styles.panelTitle}><SlidersHorizontal size={15}/><h2>Adjustments</h2><button onClick={reset} disabled={!photo || !dirty} aria-label="Reset all adjustments" title="Reset all adjustments"><RotateCcw size={14}/></button></div><div className={styles.adjustmentHeader}><span className={styles.label}>MAKE IT YOURS</span><span>{photo ? activePreset : 'Original'}</span></div>
        {CONTROL_GROUPS.map(group => <fieldset key={group.name} className={styles.controlGroup} disabled={!photo}><legend><span style={{background:group.color}}/>{group.name}</legend>{group.controls.map(control => <div className={styles.control} key={control.key}><div><label htmlFor={control.key}>{control.label}</label><output htmlFor={control.key}>{control.key === 'warmth' && values[control.key] > 0 ? '+' : ''}{values[control.key]}</output></div><input id={control.key} type="range" min={control.min} max={control.max} step="1" value={values[control.key]} style={{ '--control-color': group.color, '--range-progress': `${(values[control.key]-control.min)/(control.max-control.min)*100}%` } as CSSProperties} onChange={e => { invalidateEditedWork(); enhancementFeedback.current = ''; setPreviewReady(false); setValues(current => ({ ...current, [control.key]: Number(e.target.value) })); setActivePreset('Custom'); setStatus('Rendering your adjustment…') }} onPointerUp={flushPreview} onKeyUp={flushPreview}/><div className={styles.rangeLabels}><span>{control.min}</span><span>{control.max > 0 && control.min < 0 ? '+' : ''}{control.max}</span></div></div>)}</fieldset>)}
        <div className={styles.resetSection}><button className="button secondary" onClick={reset} disabled={!photo || !dirty}><RotateCcw size={13}/>Reset adjustments</button><p>Every adjustment starts from your original.</p></div>
      </aside>
    </main>
    <footer className={styles.studioFooter}><span><span className="status-dot"/> LUMALAB / CREATIVE WORKSPACE</span><span>LIGHT. COLOUR. CREATE.</span><span>ONE ORIGINAL. YOUR PERSPECTIVE.</span></footer>
    <dialog ref={dialog} className={styles.dialog} onCancel={() => setModal(null)} onClose={() => setModal(null)} onClick={e => { if (e.target === e.currentTarget) { const r=e.currentTarget.getBoundingClientRect(); if(e.clientX<r.left || e.clientX>r.right || e.clientY<r.top || e.clientY>r.bottom) setModal(null) } }} aria-labelledby="dialog-title" aria-describedby="dialog-description">
      <div className={styles.dialogTop}><span className="eyebrow">{modal === 'export' ? 'THE FINAL FRAME' : 'A LITTLE ASSISTANCE'}</span><button className="icon-button" aria-label="Close dialog" onClick={() => setModal(null)}><X size={18}/></button></div>
      <div className={styles.dialogIcon}>{modal === 'export' ? <Download size={27}/> : <Sparkles size={27}/>}</div>
      <h2 id="dialog-title">{modal === 'export' ? 'Your photograph, ready for the world.' : 'A balanced starting point.'}</h2>
      <p id="dialog-description">{modal === 'export' ? 'Download a full-resolution JPEG using the adjustments shown in your workspace.' : 'Auto Enhance analyses your original and suggests a complete set of adjustments. Your current edits stay in place if the analysis cannot finish.'}</p>
      {error && <div role="alert" className={styles.error}><Info size={16}/><span>{error}</span></div>}
      {modal === 'export' && <dl className={styles.exportDetails}><div><dt>Format</dt><dd>JPEG</dd></div><div><dt>Quality</dt><dd>92 / 100</dd></div><div><dt>Resolution</dt><dd>{photo?.width} × {photo?.height}</dd></div><div><dt>Look</dt><dd>{activePreset}</dd></div></dl>}
      <div className={styles.serviceNote}><Info size={15}/><span>Private processing. Your original remains unchanged.</span></div>
      <button className="button primary" disabled={modal === 'export' ? (!previewReady || exportMutation.isPending) : enhancementMutation.isPending} onClick={() => { if (modal === 'export') void downloadExport(); else void autoEnhance() }}>
        {modal === 'export' ? (exportMutation.isPending ? 'Preparing JPEG…' : 'Download JPEG') : (enhancementMutation.isPending ? 'Analyzing original…' : 'Apply suggestions')}
        {modal === 'export' ? <Download size={16}/> : <Sparkles size={16}/>}
      </button>
    </dialog>
  </div>
}
