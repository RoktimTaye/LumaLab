import { Fragment, useEffect, useRef, useState, type CSSProperties, type DragEvent } from 'react'

import { Link } from '@tanstack/react-router'

import { useMutation } from '@tanstack/react-query'

import { ArrowLeft, ArrowUpRight, Check, ChevronRight, Crop as CropIcon, Download, ImagePlus, Info, Layers, LoaderCircle, Maximize2, RotateCcw, ScanLine, ShieldCheck, SlidersHorizontal, Sparkles, Undo2, Redo2, Upload, X } from 'lucide-react'

import { Brand } from '../components/Brand'

import { RGBCurveEditor } from '../components/RGBCurveEditor'

import { identityCurves, curvesAreNeutral } from '../lib/curves'

import { getPreset, type RGBCurves, type Preset as CatalogPreset } from '../lib/api'

import { CropEditor } from '../components/CropEditor'

import { DetailPreview } from '../components/DetailPreview'

import type { Crop } from '../lib/crop'

import { PhotoPreview } from '../components/PhotoPreview'

import { CONTROL_GROUPS, loadPhoto, NEUTRAL, PRESETS, PRESET_GROUPS, type Adjustments, type LocalPhoto } from '../lib/editor'

import { ApiError, deleteImage, enhanceImage, exportImage, getOriginalPreview, getPreview, uploadImage, type NaturalEnhancement, type EnhancementFinding } from '../lib/api'

import styles from './Studio.module.css'

import { Histogram } from '../components/Histogram'
import { WhiteBalancePicker } from '../components/WhiteBalancePicker'
import { geometrySize } from '../lib/manual'



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



function presetId(name: string): string {

  return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')

}



export function Studio() {

  const uploadMutation = useMutation({ mutationFn: ({ file, signal }: { file: File; signal: AbortSignal }) => uploadImage(file, signal), gcTime: 0 })

  const enhancementMutation = useMutation({ mutationFn: ({ imageId, token, signal }: { imageId: string; token: string; signal: AbortSignal }) => enhanceImage(imageId, token, signal), gcTime: 0 })

  const exportMutation = useMutation({ mutationFn: ({ imageId, token, adjustments, crop, enhancement, curves, signal }: { imageId: string; token: string; adjustments: Adjustments; crop: Crop | null; enhancement: NaturalEnhancement | null; curves: RGBCurves; signal: AbortSignal }) => exportImage(imageId, token, adjustments, signal, crop, enhancement, curves), gcTime: 0 })

  const deleteMutation = useMutation({ mutationFn: ({ imageId, token }: { imageId: string; token: string }) => deleteImage(imageId, token), gcTime: 0 })

  const [photo, setPhoto] = useState<StudioPhoto | null>(null)

  const [curves, setCurves] = useState(identityCurves)

  const [values, setValues] = useState<Adjustments>({ ...NEUTRAL })

  const [enhancement, setEnhancement] = useState<NaturalEnhancement | null>(null)

  const [assessment, setAssessment] = useState<EnhancementFinding[]>([])

  const [crop, setCrop] = useState<Crop | null>(null)

  const [renderedCrop, setRenderedCrop] = useState<Crop | null>(null)

  const [cropEditing, setCropEditing] = useState(false)

  const [histogramVisible, setHistogramVisible] = useState(false)
  const [whiteBalanceOpen,setWhiteBalanceOpen] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)

  const [activePreset, setActivePreset] = useState('Original')

  const [compare, setCompare] = useState(false)

  const [split, setSplit] = useState(50)

  const [previewReady, setPreviewReady] = useState(false)
  const [previewInteracting,setPreviewInteracting] = useState(false)
  const previewGestureHeld = useRef(false)

  const [previewFlush, setPreviewFlush] = useState(0)

  const [mobilePanel, setMobilePanel] = useState<'presets' | 'adjustments' | null>(null)
  const [mobileTool, setMobileTool] = useState('menu')

  const [loading, setLoading] = useState(false)

  const [dragging, setDragging] = useState(false)

  const [error, setError] = useState('')

  const [status, setStatus] = useState('')

  const [modal, setModal] = useState<'enhance' | 'export' | null>(null)

  const fileInput = useRef<HTMLInputElement>(null)

  const dialog = useRef<HTMLDialogElement>(null)

  const detailTrigger = useRef<HTMLButtonElement>(null)

  const requestId = useRef(0)

  const currentPhoto = useRef<StudioPhoto | null>(null)

  const previewController = useRef<AbortController | null>(null)

  const presetCache = useRef(new Map<string, CatalogPreset>())

  const presetRequests = useRef(new Map<string, Promise<CatalogPreset>>())

  const presetSelectionRevision = useRef(0)

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



  type EditSnapshot = { values: Adjustments; curves: RGBCurves; crop: Crop | null; enhancement: NaturalEnhancement | null; activePreset: string; assessment: EnhancementFinding[] }

  const history = useRef<{ imageId: string; entries: EditSnapshot[]; index: number }>({ imageId:'', entries:[], index:-1 })

  const restoring = useRef(false)

  const [, refreshHistory] = useState(0)

  const snapshot: EditSnapshot = { values, curves, crop, enhancement, activePreset, assessment }

  const latestSnapshot = useRef(snapshot)

  latestSnapshot.current = snapshot

  const snapshotKey = JSON.stringify(snapshot)

  useEffect(() => {

    if (!photo) return

    if (history.current.imageId !== photo.imageId) {

      history.current = { imageId:photo.imageId, entries:[structuredClone(latestSnapshot.current)], index:0 }

      refreshHistory(n=>n+1)

      return

    }

    if (restoring.current) { restoring.current=false; return }

    const timer = window.setTimeout(()=>{

      const state=history.current

      if (JSON.stringify(state.entries[state.index]) === snapshotKey) return

      state.entries=state.entries.slice(0,state.index+1)

      state.entries.push(structuredClone(latestSnapshot.current))

      if (state.entries.length>100) state.entries.shift()

      state.index=state.entries.length-1

      refreshHistory(n=>n+1)

    },200)

    return ()=>window.clearTimeout(timer)

  },[photo?.imageId,snapshotKey])

  function travelHistory(direction: -1 | 1) {

    const state=history.current

    if (!photo || loading) return

    if (JSON.stringify(state.entries[state.index]) !== JSON.stringify(latestSnapshot.current)) {

      state.entries=state.entries.slice(0,state.index+1)

      state.entries.push(structuredClone(latestSnapshot.current)); state.index=state.entries.length-1

    }

    const index=state.index+direction

    if (index<0 || index>=state.entries.length) return

    invalidateEditedWork(); presetSelectionRevision.current++

    const target=structuredClone(state.entries[index]); state.index=index; restoring.current=true

    setValues(target.values); setCurves(target.curves); setCrop(target.crop); setEnhancement(target.enhancement)

    setActivePreset(target.activePreset); setAssessment(target.assessment); setPreviewReady(false)

    enhancementFeedback.current=''; setError(''); setStatus(direction<0 ? 'Undid edit.' : 'Redid edit.')

    refreshHistory(n=>n+1)

  }

  function setGeometry(patch: Partial<Adjustments>) {

    if(Object.entries(patch).every(([key,value])=>values[key as keyof Adjustments]===value))return
    if(previewGestureHeld.current)setPreviewInteracting(true)
    invalidateEditedWork(); presetSelectionRevision.current++; enhancementFeedback.current=''

    setValues(current=>({...current,...patch})); setPreviewReady(false); setActivePreset('Custom')

  }



  useEffect(()=>{
    if (!mobilePanel || !window.matchMedia('(max-width: 767px)').matches) return
    document.getElementById(mobilePanel === 'presets' ? 'studio-presets-panel' : 'studio-adjustments-panel')?.scrollTo({top:0})
  },[mobilePanel,mobileTool])

  useEffect(()=>{
    const finish=()=>{previewGestureHeld.current=false;setPreviewInteracting(false)}
    window.addEventListener('pointerup',finish)
    window.addEventListener('pointercancel',finish)
    window.addEventListener('keyup',finish)
    window.addEventListener('blur',finish)
    return()=>{
      window.removeEventListener('pointerup',finish)
      window.removeEventListener('pointercancel',finish)
      window.removeEventListener('keyup',finish)
      window.removeEventListener('blur',finish)
    }
  },[])

  function openMobileTool(tool: string) {
    setMobileTool(tool)
    setMobilePanel('adjustments')
  }
  useEffect(()=>{
    if (!mobilePanel) return
    const close=(event: KeyboardEvent)=>{if(event.key==='Escape' && !document.querySelector('dialog[open]'))setMobilePanel(null)}
    window.addEventListener('keydown',close)
    return()=>window.removeEventListener('keydown',close)
  },[mobilePanel])

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

    const requestKey = `${photo.imageId}:${JSON.stringify(values)}:${JSON.stringify(crop)}:${JSON.stringify(enhancement)}:${JSON.stringify(curves)}`

    const immediate = previewNow.current

    previewNow.current = false

    const isNeutral = Object.entries(values).every(([key, value]) => value === NEUTRAL[key as keyof Adjustments])

    if (isNeutral && curvesAreNeutral(curves) && !crop && (!enhancement || enhancement.strength === 0)) {

      setRenderedCrop(null)

      renderedPreviewKey.current = requestKey

      const current = currentPhoto.current

      if (current?.imageId === photo.imageId && current.previewUrl !== current.originalPreviewUrl) {

        URL.revokeObjectURL(current.previewUrl)

        const next = { ...current, previewUrl: current.originalPreviewUrl, url: current.originalPreviewUrl }

        currentPhoto.current = next

        setPhoto(next)

      }

      setPreviewReady(true)

      if (!enhancementFeedback.current) setStatus('')

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

        const result = await getPreview(photo.imageId, photo.accessToken, revision, values, controller.signal, crop, enhancement, curves)

        if (controller.signal.aborted || currentPhoto.current?.imageId !== photo.imageId || previewRevision.current !== revision) return

        if (result.revision !== String(revision)) throw new Error('The preview response did not match the latest settings. Try again.')

        const current = currentPhoto.current

        if (!current || current.imageId !== photo.imageId) return

        const previewUrl = URL.createObjectURL(result.blob)

        // Decode off-screen before swapping the visible image. Keep the current
        // preview intact if a newer adjustment supersedes this response.
        const decoded = new Image()
        decoded.src = previewUrl
        try {
          await decoded.decode()
        } catch (caught) {
          URL.revokeObjectURL(previewUrl)
          throw caught
        }
        if (controller.signal.aborted || currentPhoto.current?.imageId !== photo.imageId || previewRevision.current !== revision) {
          URL.revokeObjectURL(previewUrl)
          return
        }

        if (current.previewUrl !== current.originalPreviewUrl) {
          const previousUrl = current.previewUrl
          window.requestAnimationFrame(() => window.requestAnimationFrame(() => URL.revokeObjectURL(previousUrl)))
        }

        const next = { ...current, previewUrl, url: previewUrl }

        currentPhoto.current = next

        renderedPreviewKey.current = requestKey

        setRenderedCrop(crop)

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

  }, [photo?.imageId, photo?.accessToken, values, crop, enhancement, curves, previewFlush])



  function flushPreview() {

    const current = currentPhoto.current

    if (!current) return

    const requestKey = `${current.imageId}:${JSON.stringify(values)}:${JSON.stringify(crop)}:${JSON.stringify(enhancement)}:${JSON.stringify(curves)}`

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

    exportController.current?.abort()

  }

  function reset() { invalidateEditedWork(); setCrop(null); enhancementFeedback.current = ''; setEnhancement(null); setAssessment([]); setCurves(identityCurves()); setValues({ ...NEUTRAL }); setActivePreset('Original'); setStatus('All adjustments reset to Original.') }

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

    setCrop(null); setRenderedCrop(null); setCropEditing(false)

    setEnhancement(null); setAssessment([])

    setPhoto(next); setCurves(identityCurves()); setValues({ ...NEUTRAL }); setActivePreset('Original'); setCompare(false); setSplit(50)

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

      exportController.current?.abort()

      setCurves(identityCurves())

      setValues({ ...NEUTRAL, ...result.adjustments })

      setEnhancement(result.recipe ?? null)

      setAssessment(result.assessment ?? [])

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

  async function selectPreset(preset: (typeof PRESETS)[number]) {

    if (!photo || loading) return

    const selectionRevision = ++presetSelectionRevision.current

    const imageId = photo.imageId

    const id = presetId(preset.name)

    const apply = (values: Adjustments) => {

      invalidateEditedWork()

      enhancementFeedback.current = ''

      setError('')

      setEnhancement(null); setAssessment([]); setPreviewReady(false)

      setCurves(identityCurves()); setValues({ ...NEUTRAL, ...values }); setActivePreset(preset.name)

    }

    const saved = presetCache.current.get(id)

    if (saved) {

      apply({ brightness: saved.brightness, contrast: saved.contrast, saturation: saved.saturation, warmth: saved.warmth, sharpness: saved.sharpness, vignette: saved.vignette })

      setStatus(`${preset.name} preset applied.`)

      return

    }

    apply(preset.values)

    setStatus(`Applying ${preset.name} while loading its saved version…`)

    const revisionAtSelection = editRevision.current
    let request = presetRequests.current.get(id)

    if (!request) {

      request = getPreset(id)

      presetRequests.current.set(id, request)

    }

    try {

      const storedPreset = await request

      presetCache.current.set(id, storedPreset)

      if (selectionRevision !== presetSelectionRevision.current || currentPhoto.current?.imageId !== imageId || editRevision.current !== revisionAtSelection) return

      apply({ brightness: storedPreset.brightness, contrast: storedPreset.contrast, saturation: storedPreset.saturation, warmth: storedPreset.warmth, sharpness: storedPreset.sharpness, vignette: storedPreset.vignette })

      setStatus(`${preset.name} preset synced from the backend.`)

    } catch (caught) {

      if (selectionRevision !== presetSelectionRevision.current || currentPhoto.current?.imageId !== imageId || editRevision.current !== revisionAtSelection) return

      setError(errorMessage(caught, 'Could not load this saved preset. The local preview remains applied.'))

    } finally {

      if (presetRequests.current.get(id) === request) presetRequests.current.delete(id)

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

      const result = await exportMutation.mutateAsync({ imageId: target.imageId, token: target.accessToken, adjustments: snapshot, crop, enhancement, curves, signal: controller.signal })

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

  const [displayWidth, displayHeight] = geometrySize((previewReady ? renderedCrop : crop)?.width ?? photo?.width ?? 1, (previewReady ? renderedCrop : crop)?.height ?? photo?.height ?? 1, values)

  const dirty = !curvesAreNeutral(curves) || crop !== null || enhancement !== null || Object.entries(values).some(([key,value]) => value !== NEUTRAL[key as keyof Adjustments])



  return <div className={styles.studio}>

    <header className={styles.header}><Brand /><div className={styles.breadcrumb}><ChevronRight size={12} /><span>Editing Studio</span><span className={styles.version}>V.01</span></div><div className={styles.headerActions}><div className={styles.historyButtons}><button title="Undo edit" aria-label="Undo edit" disabled={!photo || loading || history.current.index <= 0 && JSON.stringify(history.current.entries[0]) === snapshotKey} onClick={()=>travelHistory(-1)}><Undo2 size={20} aria-hidden="true"/></button><button title="Redo edit" aria-label="Redo edit" disabled={!photo || loading || history.current.index >= history.current.entries.length-1} onClick={()=>travelHistory(1)}><Redo2 size={20} aria-hidden="true"/></button></div><Link to="/" className={styles.backLink}><ArrowLeft size={14} /> Back to home</Link><button className="button primary" disabled={!photo || loading || !previewReady || exportMutation.isPending} onClick={event => { lastTrigger.current = event.currentTarget; setModal('export') }}><Download size={15} /><span>{exportMutation.isPending ? 'Exporting…' : 'Export image'}</span></button></div></header>

    <input ref={fileInput} type="file" className="sr-only" tabIndex={-1} aria-label="Photograph file" accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp" onChange={e => { const file = e.target.files?.[0]; if (file) void upload(file); e.target.value = '' }} />

    <main id="main" className={`${styles.workspace} ${mobilePanel ? styles.mobileSheetOpen : ''}`}>

      <aside className={`${styles.leftPanel} ${mobilePanel === 'presets' ? styles.mobileVisible : ''}`} aria-label="Upload and presets" id="studio-presets-panel"><div className={styles.mobileSheetHeading}><h2>Styles & photo</h2><button onClick={()=>setMobilePanel(null)} aria-label="Close styles"><Check size={20}/><span>Done</span></button></div>

        <div className={styles.panelTitle}><Layers size={15}/><h2>Photo & presets</h2></div>

        <div className={styles.uploadSection}><span className={styles.label}>Photograph</span><button className={styles.uploadButton} onClick={() => fileInput.current?.click()} disabled={loading}><Upload size={17}/>{photo ? 'Replace photograph' : 'Upload photograph'}<span>+</span></button><p>JPG, PNG or WebP · Up to 10 MB<br/>24 MP · 10,000 px per side</p></div>

        <div className={styles.presetSection}><div className={styles.sectionLabel}><span className={styles.label}>Presets</span><span>{String(PRESETS.length).padStart(2, '0')}</span></div><p>{PRESETS.length} looks. Choose a starting point.</p>{PRESET_GROUPS.map(group => <details className={styles.presetGroup} key={group.name} open={group.name === 'Most Popular'}><summary>{group.name}<span>{group.presets.length}</span></summary><div className={styles.presetList}>{group.presets.map((preset,index) => <button key={preset.name} disabled={!photo || loading} aria-pressed={activePreset === preset.name} className={`${styles.preset} ${activePreset === preset.name && photo ? styles.activePreset : ''}`} onClick={() => void selectPreset(preset)}><img src={photo?.originalPreviewUrl || '/images/alpine.jpg'} alt="" style={{filter:`saturate(${preset.values.saturation / 100}) contrast(${preset.values.contrast / 100}) sepia(${preset.values.warmth > 0 ? .35 : 0})`}}/><span><strong>{preset.name}{preset.popular && <em className={styles.popularTag}>POPULAR</em>}</strong><small>{preset.description}</small></span>{activePreset === preset.name && photo ? <Check size={14}/> : <span className={styles.presetNumber}>0{index+1}</span>}</button>)}</div></details>)}</div>

        <div className={styles.enhanceSection}><div><Sparkles size={17}/><span>Automatic adjustments</span></div><p>Balance the light and colour, then refine the result.</p><button className="button secondary" disabled={!photo || loading || enhancementMutation.isPending} onClick={event => { lastTrigger.current = event.currentTarget; setModal('enhance') }}><Sparkles size={14}/>{enhancementMutation.isPending ? 'Analyzing…' : 'Auto Enhance'}<ArrowUpRight size={14}/></button></div>

        <div className={styles.preserveNote}><ShieldCheck size={14}/><span>Your original stays untouched.</span></div>

      </aside>



      <section className={styles.center} aria-label="Photograph workspace">

        <div className={styles.workspaceToolbar}><div><span className="status-dot"/><h1>{photo ? photo.name : 'Photo preview'}</h1></div><span className={styles.workspaceMode}>{photo ? (previewReady ? activePreset : 'Updating preview…') : 'No photo selected'}</span><button type="button" className={styles.histogramToggle} disabled={!photo} aria-pressed={histogramVisible} aria-controls="photo-histogram" onClick={()=>setHistogramVisible(visible=>!visible)}>{histogramVisible ? 'Hide histogram' : 'Show histogram'}</button></div>

        <div className={`${styles.canvas} ${dragging ? styles.dragging : ''}`} onDragOver={e => { e.preventDefault(); setDragging(true) }} onDragLeave={e => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragging(false) }} onDrop={drop}>

          {photo ? <><div className={styles.imageContainer} style={{ '--photo-ratio': displayWidth / displayHeight } as CSSProperties}><PhotoPreview src={photo.previewUrl} originalSrc={photo.originalPreviewUrl} name={photo.name} values={values} curves={curves} compare={compare} split={split} onSplit={setSplit} crop={previewReady ? renderedCrop : crop} originalWidth={photo.width} originalHeight={photo.height} authoritative={previewReady && !previewInteracting} eager/>{histogramVisible && <div id="photo-histogram" className={styles.histogramOverlay}><Histogram src={photo.previewUrl} originalSrc={photo.originalPreviewUrl} updating={!previewReady || previewInteracting} values={values} curves={curves} crop={crop} originalWidth={photo.width} originalHeight={photo.height}/></div>}</div>{loading && <div className={styles.loadingOverlay}><LoaderCircle className={styles.spinner} size={22}/><span>Uploading photograph…</span></div>}</> : <div className={styles.emptyState}><div className={styles.emptyIcon}><ImagePlus size={34} strokeWidth={1}/><span>+</span></div><h2>Open a photograph</h2><p>Drag a photo here or choose one from your device.</p><button className="button primary" onClick={() => fileInput.current?.click()} disabled={loading}>{loading ? <LoaderCircle className={styles.spinner} size={17}/> : <Upload size={16}/>} {loading ? 'Uploading photograph…' : 'Choose a photograph'}</button><span className={styles.uploadLimits}>JPG, PNG, WEBP · MAX 10 MB · 24 MP</span><div className={styles.sampleDivider}><span/>or<span/></div><button className={styles.sampleButton} onClick={() => void useSample()} disabled={loading}><img src="/images/alpine.jpg" alt="" width="47" height="36"/><span>Try a sample photograph<small>See how the editor works.</small></span><ArrowUpRight size={16}/></button></div>}

          {dragging && <div className={styles.dropOverlay}><Upload size={28}/><span>Drop one photograph to begin</span></div>}

        </div>

        <div className={styles.workspaceBottom}><div className={styles.imageInfo}>{photo ? <><span title={photo.name}>{photo.name}</span><small>{displayWidth} × {displayHeight} <i>·</i> {photo.format}</small></> : <><span>No photograph selected</span><small>Upload a photograph to begin.</small></>}</div><button disabled={!photo || loading || exportMutation.isPending} onClick={() => setCropEditing(true)}><CropIcon size={15}/><span>Crop</span></button><button ref={detailTrigger} className={styles.detailButton} aria-label="100% detail" title="Inspect full-resolution detail" disabled={!photo || loading || !previewReady || exportMutation.isPending} onClick={() => setDetailOpen(true)}><Maximize2 size={15}/><span>100% detail</span></button><span className={styles.fitLabel}><Maximize2 size={13}/>Fit</span><button className={compare ? styles.compareActive : ''} disabled={!photo} aria-pressed={compare} onClick={() => setCompare(!compare)}><ScanLine size={15}/><span>Compare</span></button></div>

        {error && <div role="alert" className={styles.error}><Info size={16}/><span>{error}</span><button aria-label="Dismiss error" onClick={() => setError('')}><X size={15}/></button></div>}

        {status && <div role="status" className={styles.status}>{status}</div>}

      </section>



      <div className={styles.mobileToolStrip} role="group" aria-label="Quick editing tools">
        <button disabled={!photo} onClick={()=>openMobileTool('light')}><SlidersHorizontal size={23}/><span>Tune image</span></button>
        <button disabled={!photo} onClick={()=>openMobileTool('colour')}><Layers size={23}/><span>Colour</span></button>
        <button disabled={!photo} onClick={()=>openMobileTool('curves')}><ScanLine size={23}/><span>Curves</span></button>
        <button disabled={!photo || loading} onClick={()=>setCropEditing(true)}><CropIcon size={23}/><span>Crop</span></button>
        <button disabled={!photo} onClick={()=>openMobileTool('geometry')}><RotateCcw size={23}/><span>Rotate</span></button>
        <button disabled={!photo} onClick={()=>openMobileTool('detail')}><Maximize2 size={23}/><span>Details</span></button>
        <button disabled={!photo} onClick={()=>setWhiteBalanceOpen(true)}><ScanLine size={23}/><span>White balance</span></button>
      </div>
      <div className={styles.mobileTabs} role="group" aria-label="Editing panels">
        <button aria-pressed={mobilePanel === 'presets'} aria-expanded={mobilePanel === 'presets'} aria-controls="studio-presets-panel" onClick={()=>setMobilePanel(current=>current==='presets'?null:'presets')}><Layers size={21}/><span>Styles</span></button>
        <button aria-pressed={mobilePanel === 'adjustments'} aria-expanded={mobilePanel === 'adjustments'} aria-controls="studio-adjustments-panel" onClick={()=>{setMobileTool('menu');setMobilePanel(current=>current==='adjustments' && mobileTool==='menu'?null:'adjustments')}}><SlidersHorizontal size={21}/><span>Tools</span></button>
        <button disabled={!photo || loading || !previewReady || exportMutation.isPending} onClick={event=>{lastTrigger.current=event.currentTarget;setModal('export')}}><Download size={21}/><span>Export</span></button>
      </div>



      <aside className={`${styles.rightPanel} ${mobilePanel === 'adjustments' ? styles.mobileVisible : ''}`} onPointerDownCapture={event=>{const target=event.target;if(target instanceof Element && (target.matches('input[type="range"]') || target.closest('[class*="graph"]')))previewGestureHeld.current=true}} onKeyDownCapture={event=>{if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End','PageUp','PageDown'].includes(event.key))previewGestureHeld.current=true}} aria-label="Image adjustments" id="studio-adjustments-panel" data-mobile-tool={mobileTool}><div className={styles.mobileSheetHeading}><h2>{mobileTool === 'menu' ? 'All tools' : {light:'Tune image',colour:'Colour & white balance',detail:'Details & vignette',curves:'RGB curves',geometry:'Rotate & straighten',enhance:'Auto Enhance',reset:'Reset edits'}[mobileTool] ?? 'Tools'}</h2><button onClick={()=>setMobilePanel(null)} aria-label="Close tools"><Check size={20}/><span>Done</span></button></div>
        <div className={styles.mobileToolMenu}>
          {[
            ['light','Tune image'],['colour','Colour & white balance'],['detail','Details & vignette'],['curves','RGB curves'],['geometry','Rotate & straighten'],
          ].map(([tool,label])=><button key={tool} disabled={!photo} onClick={()=>openMobileTool(tool)}><SlidersHorizontal size={22}/><span>{label}</span></button>)}
          <button disabled={!photo || loading} onClick={()=>setCropEditing(true)}><CropIcon size={22}/><span>Crop</span></button>
          <button disabled={!photo} onClick={()=>setWhiteBalanceOpen(true)}><ScanLine size={22}/><span>White balance picker / auto</span></button>
          <button disabled={!photo || loading || enhancementMutation.isPending} onClick={event=>{lastTrigger.current=event.currentTarget;setModal('enhance')}}><Sparkles size={22}/><span>Auto Enhance</span></button>
          {enhancement && <button onClick={()=>openMobileTool('enhance')}><Sparkles size={22}/><span>Enhance strength & decisions</span></button>}
          <button disabled={!photo || loading || !previewReady} onClick={event=>{detailTrigger.current=event.currentTarget;setDetailOpen(true)}}><Maximize2 size={22}/><span>100% detail</span></button>
          <button disabled={!photo} aria-pressed={compare} onClick={()=>setCompare(current=>!current)}><ScanLine size={22}/><span>{compare?'Hide comparison':'Compare original'}</span></button>
          <button disabled={!photo} aria-pressed={histogramVisible} onClick={()=>setHistogramVisible(current=>!current)}><Layers size={22}/><span>{histogramVisible?'Hide histogram':'Show histogram'}</span></button>
          <button disabled={loading} onClick={()=>fileInput.current?.click()}><Upload size={22}/><span>{photo?'Replace photograph':'Upload photograph'}</span></button>
          <button disabled={!photo || !dirty} onClick={()=>openMobileTool('reset')}><RotateCcw size={22}/><span>Reset all edits</span></button>
        </div>
        <div className={styles.panelTitle}><SlidersHorizontal size={15}/><h2>Adjustments</h2><button onClick={reset} disabled={!photo || !dirty} aria-label="Reset all adjustments" title="Reset all adjustments"><RotateCcw size={14}/></button></div><div className={styles.adjustmentHeader}><span className={styles.label}>Current look</span><span>{photo ? activePreset : 'Original'}</span></div>

        {enhancement && <fieldset data-tool="enhance" className={styles.controlGroup}><legend><Sparkles size={13}/>Auto Enhance</legend><div className={styles.control}><div><label htmlFor="enhancement-strength">Auto Enhance strength</label><output htmlFor="enhancement-strength">{Math.round((enhancement.strength ?? 1) * 100)}</output></div><input id="enhancement-strength" type="range" min="0" max="100" step="1" value={Math.round((enhancement.strength ?? 1) * 100)} style={{ '--control-color': 'var(--mint)', '--range-progress': `${(enhancement.strength ?? 1) * 100}%` } as CSSProperties} onChange={event => { if(Number(event.currentTarget.value) === Math.round((enhancement.strength ?? 1)*100))return; if(previewGestureHeld.current)setPreviewInteracting(true); invalidateEditedWork(); enhancementFeedback.current = ''; setPreviewReady(false); setEnhancement({ ...enhancement, strength: Number(event.target.value) / 100 }); setStatus('Updating Auto Enhance strength…') }} onPointerUp={flushPreview} onKeyUp={flushPreview}/><div className={styles.rangeLabels}><span>Original</span><span>Full</span></div></div></fieldset>}

        {enhancement && assessment.length > 0 && <details data-tool="enhance" className={styles.assessment}><summary>Editing decisions</summary><p>{enhancement.strength === 0 ? 'Automatic corrections are off.' : 'Automatic base; manual controls refine it.'}</p><ul tabIndex={0} aria-label="Automatic editing findings">{assessment.map((finding, index) => <li key={`${index}-${finding.issue}`}><strong>{finding.issue}</strong><p>{finding.action}</p>{finding.observation && <p>{finding.observation}</p>}</li>)}</ul></details>}

        {photo && <div data-tool="colour" className={styles.geometrySection}><button onClick={()=>setWhiteBalanceOpen(true)}>White balance eyedropper / auto</button></div>}
        <details data-tool="geometry" open={mobilePanel === 'adjustments' && mobileTool === 'geometry' ? true : undefined} className={styles.geometrySection}><summary>Rotate & straighten</summary><div className={styles.geometryButtons}><button disabled={!photo} onClick={()=>setGeometry({rotation:((values.rotation ?? 0)+270)%360 as 0|90|180|270})}>Rotate left</button><button disabled={!photo} onClick={()=>setGeometry({rotation:((values.rotation ?? 0)+90)%360 as 0|90|180|270})}>Rotate right</button><button disabled={!photo} aria-pressed={values.flip_horizontal ?? false} onClick={()=>setGeometry({flip_horizontal:!values.flip_horizontal})}>Flip horizontal</button><button disabled={!photo} aria-pressed={values.flip_vertical ?? false} onClick={()=>setGeometry({flip_vertical:!values.flip_vertical})}>Flip vertical</button></div><label htmlFor="straighten">Straighten <output>{values.straighten ?? 0}°</output></label><input id="straighten" type="range" min="-30" max="30" step=".1" value={values.straighten ?? 0} disabled={!photo} onChange={e=>setGeometry({straighten:Number(e.target.value)})} onPointerUp={flushPreview}/><p>Edges are cropped to avoid blank corners. Crop is applied before rotation.</p><button disabled={!photo} onClick={()=>setGeometry({rotation:0,straighten:0,flip_horizontal:false,flip_vertical:false})}>Reset geometry</button></details>

        {CONTROL_GROUPS.map(group => <Fragment key={group.name}><fieldset data-tool={group.name.toLowerCase()} className={styles.controlGroup} disabled={!photo}><legend><span style={{background:group.color}}/>{group.name}<button type="button" className={styles.groupReset} disabled={!photo} aria-label={`Reset ${group.name}`} onClick={()=>{invalidateEditedWork();presetSelectionRevision.current++;setValues(current=>{const next={...current};for(const control of group.controls)Object.assign(next,{[control.key]:NEUTRAL[control.key]});return next});setPreviewReady(false);setActivePreset('Custom')}}>Reset</button></legend>{group.controls.map(control => <div className={styles.control} key={control.key}><div><label htmlFor={control.key}>{control.label}</label><output htmlFor={control.key}>{control.key === 'warmth' && values[control.key] > 0 ? '+' : ''}{values[control.key] ?? 0}</output></div><input id={control.key} type="range" min={control.min} max={control.max} step={control.step ?? 1} value={values[control.key] ?? 0} style={{ '--control-color': group.color, '--range-progress': `${((values[control.key] ?? 0)-control.min)/(control.max-control.min)*100}%` } as CSSProperties} onChange={e => { const nextValue = Number(e.currentTarget.value); if(nextValue === (values[control.key] ?? 0))return; if(previewGestureHeld.current)setPreviewInteracting(true); invalidateEditedWork(); enhancementFeedback.current = ''; setPreviewReady(false); setValues(current => ({ ...current, [control.key]: nextValue })); setActivePreset('Custom'); setStatus('Rendering your adjustment…') }} onPointerUp={flushPreview} onKeyUp={flushPreview}/><div className={styles.rangeLabels}><span>{control.min}</span><span>{control.max > 0 && control.min < 0 ? '+' : ''}{control.max}</span></div></div>)}</fieldset>{group.name === 'Light' && <div data-tool="curves"><RGBCurveEditor value={curves} disabled={!photo} onChange={next => { if(JSON.stringify(next) === JSON.stringify(curves))return; if(previewGestureHeld.current)setPreviewInteracting(true); invalidateEditedWork(); enhancementFeedback.current = ''; setPreviewReady(false); setCurves(next); setActivePreset('Custom'); setStatus('Rendering your curve…') }} onCommit={flushPreview} forceOpen={mobilePanel === 'adjustments' && mobileTool === 'curves'}/></div>}</Fragment>)}

        <div data-tool="reset" className={styles.resetSection}><button className="button secondary" onClick={reset} disabled={!photo || !dirty}><RotateCcw size={13}/>Reset adjustments</button><p>Every adjustment starts from your original.</p></div>

      </aside>

    </main>


    {whiteBalanceOpen && photo && <WhiteBalancePicker src={photo.originalPreviewUrl} onClose={()=>setWhiteBalanceOpen(false)} onApply={(warmth,tint)=>setGeometry({warmth,tint})}/>}
    {detailOpen && photo && <DetailPreview imageId={photo.imageId} token={photo.accessToken} adjustments={values} curves={curves} enhancement={enhancement} crop={crop} returnFocusTo={detailTrigger.current} onClose={() => setDetailOpen(false)}/>}

    {cropEditing && photo && <CropEditor src={photo.originalPreviewUrl} width={photo.width} height={photo.height} crop={crop} onCancel={() => setCropEditing(false)} onApply={next => {

      if (JSON.stringify(next) === JSON.stringify(crop)) { setCropEditing(false); return }

      invalidateEditedWork(); exportController.current?.abort(); enhancementFeedback.current = ''; setPreviewReady(false); setCrop(next); setCropEditing(false); setError(''); setStatus(next ? 'Rendering your crop…' : 'Restoring the full photograph…')

    }}/>}

    <dialog ref={dialog} className={styles.dialog} onCancel={() => setModal(null)} onClose={() => setModal(null)} onClick={e => { if (e.target === e.currentTarget) { const r=e.currentTarget.getBoundingClientRect(); if(e.clientX<r.left || e.clientX>r.right || e.clientY<r.top || e.clientY>r.bottom) setModal(null) } }} aria-labelledby="dialog-title" aria-describedby="dialog-description">

      <div className={styles.dialogTop}><span className="eyebrow">{modal === 'export' ? 'THE FINAL FRAME' : 'A LITTLE ASSISTANCE'}</span><button className="icon-button" aria-label="Close dialog" onClick={() => setModal(null)}><X size={18}/></button></div>

      <div className={styles.dialogIcon}>{modal === 'export' ? <Download size={27}/> : <Sparkles size={27}/>}</div>

      <h2 id="dialog-title">{modal === 'export' ? 'Your photograph, ready for the world.' : 'A balanced starting point.'}</h2>

      <p id="dialog-description">{modal === 'export' ? 'Download a JPEG at the selected crop resolution using the adjustments shown in your workspace.' : 'Balance exposure, darker tones and highlights while keeping the character of your light. Adjust the strength afterward, then refine with your usual controls. Your edits stay in place if analysis cannot finish.'}</p>

      {error && <div role="alert" className={styles.error}><Info size={16}/><span>{error}</span></div>}

      {modal === 'export' && <dl className={styles.exportDetails}><div><dt>Format</dt><dd>JPEG</dd></div><div><dt>Quality</dt><dd>92 / 100</dd></div><div><dt>Resolution</dt><dd>{crop?.width ?? photo?.width} × {crop?.height ?? photo?.height}</dd></div><div><dt>Look</dt><dd>{activePreset}</dd></div></dl>}

      <div className={styles.serviceNote}><Info size={15}/><span>Private processing. Your original remains unchanged.</span></div>

      <button className={`button primary ${modal === 'enhance' ? styles.applySuggestionsAction : ''}`} disabled={modal === 'export' ? (!previewReady || exportMutation.isPending) : enhancementMutation.isPending} onClick={() => { if (modal === 'export') void downloadExport(); else void autoEnhance() }}>

        {modal === 'export' ? (exportMutation.isPending ? 'Preparing JPEG…' : 'Download JPEG') : (enhancementMutation.isPending ? 'Analyzing original…' : 'Apply suggestions')}

        {modal === 'export' ? <Download size={16}/> : <Sparkles size={16}/>}

      </button>

    </dialog>

  </div>

}

