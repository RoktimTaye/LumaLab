import { test, expect } from './fixtures'

async function jpegFixture(page: import('@playwright/test').Page, width: number, height: number) {
  const base64 = await page.evaluate(async ({width,height}) => {
    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height
    const context = canvas.getContext('2d')!
    const gradient = context.createLinearGradient(0, 0, width, height)
    gradient.addColorStop(0, '#294c63')
    gradient.addColorStop(0.48, '#86a96c')
    gradient.addColorStop(1, '#e6bc7a')
    context.fillStyle = gradient
    context.fillRect(0, 0, width, height)
    context.globalAlpha = 0.22
    for (let y = 0; y < height; y += 32) {
      context.fillStyle = y % 64 ? '#18241e' : '#f5e8c6'
      context.fillRect(0, y, width, 2)
    }
    const blob = await new Promise<Blob>(resolve => canvas.toBlob(value => resolve(value!), 'image/jpeg', 0.88))
    const bytes = new Uint8Array(await blob.arrayBuffer())
    let binary = ''
    for (let offset = 0; offset < bytes.length; offset += 0x8000) binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000))
    return btoa(binary)
  }, {width,height})
  return Buffer.from(base64, 'base64')
}

test('records laptop performance and handles the maximum supported image', async ({ page }) => {
  test.setTimeout(120_000)
  await page.setViewportSize({width:1440,height:900})
  let started = Date.now()
  await page.goto('/')
  await expect(page.getByRole('heading', {name:'Light. Colour. Create.'})).toBeVisible()
  const homeUsableMs = Date.now() - started

  await page.goto('/studio')
  const region = page.getByRole('region', {name:'Photograph workspace'})
  const input = page.getByLabel('Photograph file', {exact:true})
  const fixture12 = await jpegFixture(page, 4000, 3000)
  expect(fixture12.length).toBeLessThan(10_000_000)
  started = Date.now()
  await input.setInputFiles({name:'reference-12mp.jpg',mimeType:'image/jpeg',buffer:fixture12})
  await expect(page.getByText('reference-12mp.jpg', {exact:true})).toBeVisible()
  await expect(region.getByRole('status')).toHaveText('Original preview is ready.')
  const upload12MpMs = Date.now() - started

  await page.evaluate(() => { (window as Window & {__previewRequestStart?:number}).__previewRequestStart = performance.now() })
  await page.getByRole('button', {name:/Vivid/}).click()
  await expect(region.getByRole('status')).toHaveText('Preview is up to date.')
  const preview12MpMs = await page.evaluate(() => {
    const start = (window as Window & {__previewRequestStart?:number}).__previewRequestStart ?? 0
    return performance.getEntriesByType('resource')
      .filter((entry): entry is PerformanceResourceTiming => entry instanceof PerformanceResourceTiming && entry.name.endsWith('/preview') && entry.startTime >= start)
      .at(-1)?.duration ?? Number.POSITIVE_INFINITY
  })
  const brightness = page.getByLabel('Brightness', {exact:true})
  await brightness.evaluate(element => {
    const state = window as Window & {__lumalabSlider?:{started:number;finished:number}}
    state.__lumalabSlider = {started:0,finished:0}
    element.addEventListener('keydown', () => { state.__lumalabSlider!.started = performance.now() }, {once:true})
    element.addEventListener('input', () => requestAnimationFrame(() => { state.__lumalabSlider!.finished = performance.now() }), {once:true})
  })
  await brightness.focus()
  await page.keyboard.press('ArrowRight')
  await expect(brightness).toHaveValue('104')
  await expect.poll(() => page.evaluate(() => (window as Window & {__lumalabSlider?:{finished:number}}).__lumalabSlider?.finished ?? 0)).toBeGreaterThan(0)
  const sliderFeedbackMs = await page.evaluate(() => {
    const state = (window as Window & {__lumalabSlider?:{started:number;finished:number}}).__lumalabSlider!
    return state.finished - state.started
  })
  await expect(region.getByRole('status')).toHaveText('Preview is up to date.')

  started = Date.now()
  await page.getByRole('button', {name:'Auto Enhance'}).click()
  await page.getByRole('button', {name:'Apply suggestions'}).click()
  await expect(page.getByText('Auto Enhanced', {exact:true})).toBeVisible()
  await expect(page.getByRole('button', {name:'Export image'})).toBeEnabled()
  const enhance12MpMs = Date.now() - started

  started = Date.now()
  await page.getByRole('button', {name:'Export image'}).click()
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', {name:'Download JPEG'}).click()
  const download = await downloadPromise
  expect(await download.failure()).toBeNull()
  const export12MpMs = Date.now() - started

  const fixture24 = await jpegFixture(page, 6000, 4000)
  expect(fixture24.length).toBeLessThan(10_000_000)
  started = Date.now()
  await input.setInputFiles({name:'supported-24mp.jpg',mimeType:'image/jpeg',buffer:fixture24})
  await expect(page.getByText('supported-24mp.jpg', {exact:true})).toBeVisible({timeout:30_000})
  await expect(region.getByRole('status')).toHaveText('Original preview is ready.', {timeout:30_000})
  const upload24MpMs = Date.now() - started
  const heapBytes = await page.evaluate(() => (performance as Performance & {memory?:{usedJSHeapSize:number}}).memory?.usedJSHeapSize ?? null)

  const metrics = {homeUsableMs,upload12MpMs,preview12MpMs,sliderFeedbackMs,enhance12MpMs,export12MpMs,upload24MpMs,fixture12Bytes:fixture12.length,fixture24Bytes:fixture24.length,jsHeapBytes:heapBytes}
  console.log(`LumaLab performance (${await page.evaluate(() => navigator.userAgent)}): ${JSON.stringify(metrics)}`)
  expect(homeUsableMs).toBeLessThan(3_000)
  expect(sliderFeedbackMs).toBeLessThan(100)
  expect(preview12MpMs).toBeLessThan(1_000)
  expect(enhance12MpMs).toBeLessThan(3_000)
  expect(export12MpMs).toBeLessThan(5_000)
})
