import { test, expect } from './fixtures'
import AxeBuilder from '@axe-core/playwright'
import path from 'node:path'

const sizes = [[320,568],[360,800],[390,844],[430,932],[768,1024],[820,1180],[1024,768],[1280,800],[1440,900],[1920,1080],[2560,1440],[844,390]]

test('home and studio reflow across the required viewport matrix', async ({ page }) => {
  test.setTimeout(120_000)
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  for (const [width,height] of sizes) {
    await page.setViewportSize({width,height})
    for (const route of ['/', '/studio']) {
      await page.goto(route)
      await page.evaluate(() => document.fonts.ready)
      await expect(page.locator('h1')).toBeVisible()
      const overflow = await page.evaluate(() => ({ width:document.documentElement.scrollWidth, offenders:[...document.querySelectorAll('main *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>({tag:e.tagName,cls:e.className,right:e.getBoundingClientRect().right})).slice(0,10) }))
      expect(overflow.width, `${route} at ${width}: ${JSON.stringify(overflow.offenders)}`).toBeLessThanOrEqual(width)
    }
  }
  expect(errors).toEqual([])
})

test('presets, keyboard controls, comparison and reset preserve the original', async ({ page }, testInfo) => {
  await page.setViewportSize({width:1440,height:900})
  await page.goto('/studio')
  await page.getByRole('button', { name: 'Try a sample photograph' }).click()
  await page.getByRole('button', { name: /Golden Hour/ }).click()
  await expect(page.getByLabel('Warmth', {exact:true})).toHaveValue('22')
  await page.getByRole('button', { name: /Monochrome/ }).click()
  await expect(page.getByLabel('Saturation', {exact:true})).toHaveValue('0')
  await expect(page.getByLabel('Warmth', {exact:true})).toHaveValue('0')
  await page.getByLabel('Brightness', {exact:true}).focus()
  await page.keyboard.press('ArrowRight')
  await expect(page.getByLabel('Brightness', {exact:true})).toHaveValue('103')
  await expect(page.getByText('Custom', {exact:true})).toBeVisible()
  await page.getByRole('button', {name:'Compare',exact:true}).click()
  await page.getByLabel('Before and after comparison position').fill('72')
  await expect(page.getByLabel('Brightness', {exact:true})).toHaveValue('103')
  await page.getByRole('button', {name:'Reset adjustments',exact:true}).click()
  await expect(page.getByLabel('Brightness', {exact:true})).toHaveValue('100')
  await expect(page.getByLabel('Saturation', {exact:true})).toHaveValue('100')
  await page.getByRole('button', {name:'Auto Enhance'}).click()
  await page.getByRole('button', {name:'Apply suggestions'}).click()
  await expect(page.getByText('Auto Enhanced', {exact:true})).toBeVisible()
  await expect(page.getByRole('button', {name:'Export image'})).toBeEnabled()
  await page.getByRole('button', {name:'Compare',exact:true}).click()
  await page.screenshot({path:testInfo.outputPath('connected-workflow.png'),fullPage:true})
  await page.getByRole('button', {name:'Compare',exact:true}).click()
  await page.getByRole('button', {name:'Export image'}).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await expect(page.getByText('Quality', {exact:true})).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('button', {name:'Export image'})).toBeFocused()
  await page.getByRole('button', {name:'Export image'}).click()
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', {name:'Download JPEG'}).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toBe('lumalab-alpine-perspective.jpg')
  await page.reload()
  await expect(page.getByRole('button', {name:'Choose a photograph',exact:true})).toBeVisible()
})

test('connected enhancement reports an unavailable service and retries on request', async ({ page }) => {
  await page.goto('/studio')
  await page.getByRole('button', {name:'Try a sample photograph'}).click()
  await expect(page.getByText('alpine-perspective.jpg', {exact:true})).toBeVisible()
  await page.getByRole('button', {name:/Vivid/}).click()
  await expect(page.getByRole('region', {name:'Photograph workspace'}).getByRole('status')).toHaveText('Preview is up to date.')
  await expect(page.getByLabel('Saturation', {exact:true})).toHaveValue('140')
  let unavailable = true
  await page.route('**/api/v1/images/*/enhance', async route => {
    if (unavailable) {
      unavailable = false
      await route.fulfill({status:503, contentType:'application/json', body:JSON.stringify({error:{code:'service_unavailable',message:'Editing service temporarily unavailable.'}})})
    } else {
      await route.continue()
    }
  })
  await page.getByRole('button', {name:'Auto Enhance'}).click()
  await page.getByRole('button', {name:'Apply suggestions'}).click()
  await expect(page.getByRole('dialog').getByRole('alert')).toContainText('temporarily unavailable')
  await expect(page.getByLabel('Saturation', {exact:true})).toHaveValue('140')
  await page.getByRole('button', {name:'Apply suggestions'}).click()
  await expect(page.getByText('Auto Enhanced', {exact:true})).toBeVisible()
  expect(unavailable).toBe(false)
})

test('a delayed old preview cannot replace a newer edit response', async ({ page }) => {
  await page.goto('/studio')
  await page.getByRole('button', {name:'Try a sample photograph'}).click()
  await expect(page.getByText('alpine-perspective.jpg', {exact:true})).toBeVisible()
  let releaseFirst!: () => void
  const firstPreviewReady = new Promise<void>(resolve => { releaseFirst = resolve })
  let requests = 0
  await page.route('**/api/v1/images/*/preview', async route => {
    requests++
    if (requests === 1) {
      const response = await route.fetch()
      releaseFirst()
      await new Promise(resolve => setTimeout(resolve, 600))
      await route.fulfill({response}).catch(() => {})
    } else {
      await route.continue()
    }
  })
  await page.getByRole('button', {name:/Vivid/}).click()
  await firstPreviewReady
  await page.getByRole('button', {name:/Monochrome/}).click()
  await expect(page.getByLabel('Saturation', {exact:true})).toHaveValue('0')
  await expect(page.getByRole('region', {name:'Photograph workspace'}).getByRole('status')).toHaveText('Preview is up to date.')
  await page.waitForTimeout(700)
  await expect(page.getByLabel('Saturation', {exact:true})).toHaveValue('0')
  expect(requests).toBe(2)
})

test('a late failed replacement cannot overwrite a newer successful upload', async ({ page }) => {
  await page.goto('/studio')
  const input = page.getByLabel('Photograph file', {exact:true})
  let releaseFirst!: () => void
  const firstUploadStarted = new Promise<void>(resolve => { releaseFirst = resolve })
  let uploads = 0
  await page.route('**/api/v1/images', async route => {
    uploads++
    if (uploads === 1) {
      releaseFirst()
      await new Promise(resolve => setTimeout(resolve, 700))
      await route.fulfill({status:503, contentType:'application/json', body:JSON.stringify({error:{code:'service_unavailable',message:'Delayed upload failed.'}})}).catch(() => {})
    } else {
      await route.continue()
    }
  })
  await input.setInputFiles(path.resolve('public/images/alpine.jpg'))
  await firstUploadStarted
  await input.setInputFiles(path.resolve('public/images/forest.jpg'))
  await expect(page.getByText('forest.jpg', {exact:true})).toBeVisible()
  await expect(page.getByRole('region', {name:'Photograph workspace'}).getByRole('status')).toHaveText('Original preview is ready.')
  await page.waitForTimeout(800)
  await expect(page.getByText('forest.jpg', {exact:true})).toBeVisible()
  await expect(page.getByRole('alert')).toHaveCount(0)
  expect(uploads).toBe(2)
})

test('uploads validate bytes and failed replacement preserves current edits', async ({ page }) => {
  await page.setViewportSize({width:1440,height:900})
  await page.goto('/studio')
  const input = page.getByLabel('Photograph file', {exact:true})
  let uploadStarted!: () => void
  const uploadObserved = new Promise<void>(resolve => { uploadStarted = resolve })
  await page.route('**/api/v1/images', async route => {
    uploadStarted()
    await new Promise(resolve => setTimeout(resolve, 300))
    await route.continue()
  })
  await input.setInputFiles(path.resolve('public/images/alpine.jpg'))
  await uploadObserved
  await expect(page.getByRole('region', {name:'Photograph workspace'}).getByRole('status')).toHaveText('Uploading and preparing your photograph…')
  await expect(page.getByText('alpine.jpg', {exact:true})).toBeVisible()
  await page.unroute('**/api/v1/images')
  await page.getByRole('button', {name:/Vivid/}).click()
  await expect(page.getByRole('region', {name:'Photograph workspace'}).getByRole('status')).toHaveText('Preview is up to date.')
  await input.setInputFiles({name:'corrupt.jpg',mimeType:'image/jpeg',buffer:Buffer.from('not a photograph')})
  await expect(page.getByRole('alert')).toContainText('Choose a still JPG')
  await expect(page.getByLabel('Saturation', {exact:true})).toHaveValue('140')
  await expect(page.getByText('alpine.jpg', {exact:true})).toBeVisible()
  for (const mime of ['image/png','image/webp']) {
    const data = await page.evaluate(type => { const c=document.createElement('canvas');c.width=100;c.height=80;const ctx=c.getContext('2d')!;ctx.fillStyle='#94f7bc';ctx.fillRect(10,10,50,50);return c.toDataURL(type).split(',')[1] }, mime)
    await input.setInputFiles({name:`transparent.${mime.split('/')[1]}`,mimeType:mime,buffer:Buffer.from(data,'base64')})
    await expect(page.getByLabel('Saturation', {exact:true})).toHaveValue('100')
    await expect(page.getByText(`transparent.${mime.split('/')[1]}`, {exact:true})).toBeVisible()
    await expect(page.getByRole('region', {name:'Photograph workspace'}).getByRole('status')).toHaveText(/(is ready to edit|Original preview is ready)\./)
  }
  const longName = `${'long-name-'.repeat(11)}.png`
  const pngData = await page.evaluate(() => { const c=document.createElement('canvas');c.width=100;c.height=80;return c.toDataURL('image/png').split(',')[1] })
  await input.setInputFiles({name:longName,mimeType:'image/png',buffer:Buffer.from(pngData,'base64')})
  await expect(page.getByText(longName, {exact:true})).toBeVisible()
})

test('reduced motion, enlarged text, zoom-sized reflow and touch controls', async ({ browser }) => {
  const context = await browser.newContext({viewport:{width:390,height:844},hasTouch:true,isMobile:true})
  const page = await context.newPage()
  await page.emulateMedia({reducedMotion:'reduce'})
  await page.goto('/studio')
  await expect(page.getByRole('button', {name:'Try a sample photograph'})).toBeVisible()
  const reduced = await page.evaluate(() => ({behavior:getComputedStyle(document.documentElement).scrollBehavior, transition:getComputedStyle(document.querySelector('button')!).transitionDuration}))
  expect(reduced).toEqual({behavior:'auto',transition:'0s'})
  await page.addStyleTag({content:'html{font-size:200%}'})
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  await page.evaluate(() => { document.documentElement.style.fontSize='' })
  await page.setViewportSize({width:320,height:844})
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  await page.setViewportSize({width:390,height:844})
  await page.goto('/')
  const menu = page.getByRole('button', {name:'Open menu'})
  const menuBox = await menu.boundingBox()
  expect(menuBox).not.toBeNull()
  await page.touchscreen.tap(menuBox!.x + menuBox!.width / 2, menuBox!.y + menuBox!.height / 2)
  await expect(page.getByRole('navigation')).toBeVisible()
  await page.goto('/studio')
  await page.getByRole('button', {name:'Try a sample photograph'}).click()
  const adjustments = page.getByRole('button', {name:'Adjustments',exact:true})
  const adjustmentsBox = await adjustments.boundingBox()
  expect(adjustmentsBox).not.toBeNull()
  await page.touchscreen.tap(adjustmentsBox!.x + adjustmentsBox!.width / 2, adjustmentsBox!.y + adjustmentsBox!.height / 2)
  await expect(page.getByRole('complementary', {name:'Image adjustments'})).toBeVisible()
  await context.close()
})

test('mobile menu, panels and keyboard focus work', async ({ page }) => {
  await page.setViewportSize({width:360,height:800})
  await page.goto('/')
  await page.getByRole('button', {name:'Open menu'}).click()
  await expect(page.getByRole('navigation')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('button', {name:'Open menu'})).toBeFocused()
  await page.getByRole('link', {name:'Start Editing'}).first().click()
  await page.getByRole('button', {name:'Try a sample photograph'}).click()
  await page.getByRole('button', {name:'Presets & upload'}).click()
  await page.getByRole('button', {name:/Cinematic/}).click()
  await page.getByRole('button', {name:'Adjustments',exact:true}).click()
  await expect(page.getByLabel('Contrast', {exact:true})).toHaveValue('120')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
})

test('accessible landmarks, names and contrast on home and populated studio', async ({ page }) => {
  test.setTimeout(60_000)
  for (const width of [1440,360]) {
    await page.setViewportSize({width,height:900})
    for (const route of ['/', '/studio']) {
      await page.goto(route)
      if (route === '/studio') await page.getByRole('button', {name:'Try a sample photograph'}).click()
      const result = await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()
      expect(result.violations.map(v => ({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))).toEqual([])
    }
  }
})

test('capture desktop and phone views', async ({ page }, testInfo) => {
  await page.setViewportSize({width:1440,height:1000})
  await page.goto('/')
  await page.evaluate(() => document.fonts.ready)
  await page.screenshot({path:testInfo.outputPath('home-desktop.png'),fullPage:true})
  await page.goto('/studio')
  await page.screenshot({path:testInfo.outputPath('studio-empty.png'),fullPage:true})
  await page.getByRole('button', {name:'Try a sample photograph'}).click()
  await page.getByRole('button', {name:/Cinematic/}).click()
  await page.getByRole('button', {name:'Compare',exact:true}).click()
  await page.screenshot({path:testInfo.outputPath('studio-desktop.png'),fullPage:true})
  await page.setViewportSize({width:390,height:844})
  await page.screenshot({path:testInfo.outputPath('studio-mobile.png'),fullPage:true})
  await page.goto('/')
  await page.screenshot({path:testInfo.outputPath('home-mobile.png'),fullPage:true})
})
