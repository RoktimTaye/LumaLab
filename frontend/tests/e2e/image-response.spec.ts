import { test, expect } from '@playwright/test'

test('JPEG response blobs display, download and release their object URLs', async ({ page }) => {
  await page.goto('/studio')
  const result = await page.evaluate(async () => {
    const { imageResponseUrl } = await import('/src/lib/imageResponse.ts')
    const canvas = document.createElement('canvas')
    canvas.width = 8; canvas.height = 4
    const blob = await new Promise<Blob>(resolve => canvas.toBlob(value => resolve(value!), 'image/jpeg'))
    const image = await imageResponseUrl(new Response(blob))
    const element = new Image()
    element.src = image.url
    document.body.append(element)
    await element.decode()
    const dimensions = [element.naturalWidth, element.naturalHeight]
    element.remove()
    image.revoke()
    const revoked = await fetch(image.url).then(() => false, () => true)
    return { dimensions, revoked }
  })
  expect(result).toEqual({ dimensions: [8, 4], revoked: true })
  const downloadPromise = page.waitForEvent('download')
  await page.evaluate(async () => {
    const { downloadImageResponse } = await import('/src/lib/imageResponse.ts')
    const canvas = document.createElement('canvas')
    const blob = await new Promise<Blob>(resolve => canvas.toBlob(value => resolve(value!), 'image/jpeg'))
    await downloadImageResponse(new Response(blob), 'lumalab-test.jpg')
  })
  const download = await downloadPromise
  expect(download.suggestedFilename()).toBe('lumalab-test.jpg')
  const stream = await download.createReadStream()
  const chunks: Buffer[] = []
  for await (const chunk of stream!) chunks.push(chunk)
  const data = Buffer.concat(chunks)
  expect([...data.subarray(0, 2)]).toEqual([255, 216])
  expect([...data.subarray(-2)]).toEqual([255, 217])
  expect(await download.failure()).toBeNull()
})
