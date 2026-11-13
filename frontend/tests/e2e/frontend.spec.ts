import { test, expect } from '@playwright/test'
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

test('presets, keyboard controls, comparison and reset preserve the original', async ({ page }) => {
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
  await page.getByRole('button', {name:'Export image'}).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await expect(page.getByText('Editing service not connected', {exact:true})).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('button', {name:'Export image'})).toBeFocused()
  await page.reload()
  await expect(page.getByRole('button', {name:'Choose a photograph',exact:true})).toBeVisible()
})

test('uploads validate bytes and failed replacement preserves current edits', async ({ page }) => {
  await page.setViewportSize({width:1440,height:900})
  await page.goto('/studio')
  const input = page.getByLabel('Photograph file', {exact:true})
  await input.setInputFiles(path.resolve('public/images/alpine.jpg'))
  await expect(page.getByText('alpine.jpg', {exact:true})).toBeVisible()
  await page.getByRole('button', {name:/Vivid/}).click()
  await input.setInputFiles({name:'corrupt.jpg',mimeType:'image/jpeg',buffer:Buffer.from('not a photograph')})
  await expect(page.getByRole('alert')).toContainText('Choose a still JPG')
  await expect(page.getByLabel('Saturation', {exact:true})).toHaveValue('140')
  await expect(page.getByText('alpine.jpg', {exact:true})).toBeVisible()
  for (const mime of ['image/png','image/webp']) {
    const data = await page.evaluate(type => { const c=document.createElement('canvas');c.width=100;c.height=80;const ctx=c.getContext('2d')!;ctx.fillStyle='#94f7bc';ctx.fillRect(10,10,50,50);return c.toDataURL(type).split(',')[1] }, mime)
    await input.setInputFiles({name:`transparent.${mime.split('/')[1]}`,mimeType:mime,buffer:Buffer.from(data,'base64')})
    await expect(page.getByLabel('Saturation', {exact:true})).toHaveValue('100')
    await expect(page.getByText(`transparent.${mime.split('/')[1]}`, {exact:true})).toBeVisible()
  }
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

test('capture desktop and phone views', async ({ page }) => {
  await page.setViewportSize({width:1440,height:1000})
  await page.goto('/')
  await page.evaluate(() => document.fonts.ready)
  await page.screenshot({path:'screenshots/home-desktop.png',fullPage:true})
  await page.goto('/studio')
  await page.screenshot({path:'screenshots/studio-empty.png',fullPage:true})
  await page.getByRole('button', {name:'Try a sample photograph'}).click()
  await page.getByRole('button', {name:/Cinematic/}).click()
  await page.getByRole('button', {name:'Compare',exact:true}).click()
  await page.screenshot({path:'screenshots/studio-desktop.png',fullPage:true})
  await page.setViewportSize({width:390,height:844})
  await page.screenshot({path:'screenshots/studio-mobile.png',fullPage:true})
  await page.goto('/')
  await page.screenshot({path:'screenshots/home-mobile.png',fullPage:true})
})
