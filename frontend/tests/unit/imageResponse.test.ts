import { afterEach, describe, expect, it, vi } from 'vitest'
import { downloadImageResponse, imageResponseUrl } from '../../src/lib/imageResponse'

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers() })

function jpeg() {
  return new Response(new Uint8Array([255, 216, 255, 217]), { headers: { 'content-type': 'image/jpeg' } })
}

describe('image response object URLs', () => {
  it('preserves binary bytes and releases the preview URL on request', async () => {
    const create = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:preview')
    const revoke = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
    const image = await imageResponseUrl(jpeg())
    const blob = create.mock.calls[0][0] as Blob
    expect([...new Uint8Array(await blob.arrayBuffer())]).toEqual([255, 216, 255, 217])
    expect(image.url).toBe('blob:preview')
    expect(revoke).not.toHaveBeenCalled()
    image.revoke()
    expect(revoke).toHaveBeenCalledWith('blob:preview')
  })

  it('rejects JSON errors and unexpected response types without allocating a URL', async () => {
    const create = vi.spyOn(URL, 'createObjectURL')
    for (const response of [new Response('{}', { status: 401, headers: { 'content-type': 'application/json' } }),
      new Response('{}', { headers: { 'content-type': 'application/json' } }), new Response(null, { status: 204 })]) {
      await expect(imageResponseUrl(response)).rejects.toThrow('Unable to load')
    }
    expect(create).not.toHaveBeenCalled()
  })

  it('creates a blob download and releases the URL after the click', async () => {
    vi.useFakeTimers()
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:download')
    const revoke = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
    const link = { href: '', download: '', click: vi.fn(), remove: vi.fn() }
    const append = vi.fn()
    vi.stubGlobal('document', { createElement: () => link, body: { append } })
    await downloadImageResponse(jpeg(), 'lumalab-photo.jpg')
    expect(link.href).toBe('blob:download')
    expect(link.download).toBe('lumalab-photo.jpg')
    expect(append).toHaveBeenCalledWith(link)
    expect(link.click).toHaveBeenCalledOnce()
    expect(link.remove).toHaveBeenCalledOnce()
    expect(revoke).not.toHaveBeenCalled()
    vi.runAllTimers()
    expect(revoke).toHaveBeenCalledWith('blob:download')
  })

  it('releases the URL and anchor if download initiation fails', async () => {
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:failed')
    const revoke = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
    const link = { href: '', download: '', click: () => { throw new Error('failed') }, remove: vi.fn() }
    vi.stubGlobal('document', { createElement: () => link, body: { append: vi.fn() } })
    await expect(downloadImageResponse(jpeg(), 'photo.jpg')).rejects.toThrow('failed')
    expect(revoke).toHaveBeenCalledWith('blob:failed')
    expect(link.remove).toHaveBeenCalledOnce()
  })
})
