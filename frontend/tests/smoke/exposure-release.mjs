import {chromium} from '@playwright/test'
import {mkdirSync} from 'node:fs'
const browser=await chromium.launch({channel:'chrome',headless:true})
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}})
 let mime='';page.on('response',r=>{if(r.url().endsWith('/original-preview'))mime=r.headers()['content-type']})
 await page.goto(`${process.env.STUDIO_TEST_URL ?? 'http://127.0.0.1:5178'}/studio`);await page.getByLabel('Photograph file').setInputFiles('public/images/tree-lined-road-original.jpg');await page.locator('#exposure:enabled').waitFor();await page.waitForTimeout(250)
 if(!mime.startsWith('image/png'))throw new Error('Source is not lossless PNG')
 mkdirSync('tone-regression',{recursive:true});const photo=page.locator('[class*="imageContainer"]')
 for(const value of ['3','0.7','-1.4']){
  const slider=page.locator('#exposure');await slider.dispatchEvent('pointerdown',{pointerId:1,pointerType:'mouse',button:0,bubbles:true});await slider.fill(value)
  await page.waitForFunction(()=>!Array.from(document.querySelectorAll('button')).find(b=>b.textContent==='Export image')?.disabled)
  await page.waitForTimeout(180)
  await photo.screenshot({path:`tone-regression/${value}-held.png`})
  await page.locator('body').dispatchEvent('pointerup',{pointerId:1,bubbles:true});await page.waitForTimeout(250)
  if(await slider.inputValue()!==value)throw new Error('Exposure value changed at release')
  await photo.screenshot({path:`tone-regression/${value}-released.png`})
  console.log(`Exposure ${value}: numeric value preserved through pointer release`)
 }
}finally{await browser.close()}
