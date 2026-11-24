import { chromium } from '@playwright/test'
import { readFileSync } from 'node:fs'
const browser=await chromium.launch({channel:'chrome',headless:true})
const page=await browser.newPage()
const photo=readFileSync('public/images/alpine.jpg')
let delivered=0
await page.route('**/api/v1/images**',async route=>{
 const req=route.request(),url=new URL(req.url())
 if(url.pathname.endsWith('/preview')){
  await new Promise(resolve=>setTimeout(resolve,3000))
  delivered++
  await route.fulfill({status:200,contentType:'image/jpeg',body:photo,headers:{'X-Image-Revision':String(req.postDataJSON().revision)}}).catch(()=>{})
 }else if(url.pathname.endsWith('/original-preview'))await route.fulfill({status:200,contentType:'image/jpeg',body:photo})
 else if(req.method()==='POST')await route.fulfill({status:201,json:{image_id:'0123456789abcdef0123456789abcdef',access_token:'test-token',filename:'alpine.jpg',format:'JPEG',width:900,height:600,expires_at:'2027-01-01T00:00:00Z'}})
 else await route.fulfill({status:204})
})
try{
 await page.goto('http://127.0.0.1:5178/studio')
 await page.getByLabel('Photograph file').setInputFiles('public/images/alpine.jpg')
 await page.getByRole('button',{name:'Show histogram'}).click()
 const graph=page.getByRole('img',{name:'Luminance histogram, shadows on the left and highlights on the right'}).locator('path')
 await graph.waitFor()
 const before=await graph.getAttribute('d')
 await page.locator('#exposure').fill('2')
 await page.waitForFunction(old=>document.querySelector('[aria-label="Luminance histogram, shadows on the left and highlights on the right"] path')?.getAttribute('d')!==old,before,{timeout:1000})
 if(delivered!==0)throw new Error('Server already responded')
 console.log('Passed: histogram path changed with exposure before any delayed server preview arrived.')
 await page.getByRole('button',{name:'Hide histogram'}).click()
 if(await page.getByRole('region',{name:'Photo histogram'}).count())throw new Error('Histogram remained visible')
 console.log('Passed: histogram toggle still hides the graph.')
}finally{await browser.close()}
