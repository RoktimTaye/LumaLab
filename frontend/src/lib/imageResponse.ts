// Consume authorized fetch responses; credentials stay in headers, never image URLs.
export async function imageResponseUrl(response: Response) {
  if (!response.ok || response.headers.get('content-type')?.split(';')[0].trim().toLowerCase() !== 'image/jpeg') {
    throw new Error('Unable to load the image response.')
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  return { url, revoke: () => URL.revokeObjectURL(url) }
}

export async function downloadImageResponse(response: Response, filename: string) {
  const link = document.createElement('a')
  const image = await imageResponseUrl(response)
  try {
    link.href = image.url
    link.download = filename
    document.body.append(link)
    link.click()
  } catch (error) {
    image.revoke()
    throw error
  } finally {
    link.remove()
  }
  // Let the browser start consuming the download before releasing its blob URL.
  setTimeout(image.revoke, 1000)
}
