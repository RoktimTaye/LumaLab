import type { components } from './api.generated'

export type Adjustments = components['schemas']['Adjustments']
export type Enhancement = components['schemas']['Enhancement']
export type Preset = components['schemas']['Preset']
export type UploadedImage = components['schemas']['UploadedImage']

const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '')

export class ApiError extends Error {
  constructor(message: string, readonly status: number, readonly code?: string) {
    super(message)
    this.name = 'ApiError'
  }
}

type RequestOptions = {
  token?: string
  signal?: AbortSignal
  body?: BodyInit
  json?: unknown
}

async function request(path: string, method: string, options: RequestOptions = {}): Promise<Response> {
  const headers = new Headers()
  if (options.token) headers.set('Authorization', `Bearer ${options.token}`)
  let body = options.body
  if (options.json !== undefined) {
    headers.set('Content-Type', 'application/json')
    body = JSON.stringify(options.json)
  }

  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers,
    body,
    signal: options.signal,
  })
  if (!response.ok) throw await parseError(response)
  return response
}

async function parseError(response: Response): Promise<ApiError> {
  let message = `Request failed (${response.status}).`
  let code: string | undefined
  try {
    const payload: unknown = await response.json()
    if (payload && typeof payload === 'object' && 'error' in payload) {
      const detail = payload.error
      if (detail && typeof detail === 'object') {
        if ('message' in detail && typeof detail.message === 'string') message = detail.message
        if ('code' in detail && typeof detail.code === 'string') code = detail.code
      }
    }
  } catch {
    // Keep the status-based message when the server did not return JSON.
  }
  return new ApiError(message, response.status, code)
}

function imagePath(imageId: string): string {
  return `/api/v1/images/${encodeURIComponent(imageId)}`
}

export async function getHealth(signal?: AbortSignal) {
  const response = await request('/api/v1/health', 'GET', { signal })
  return response.json() as Promise<components['schemas']['HealthResponse']>
}

export async function getPresets(signal?: AbortSignal) {
  const response = await request('/api/v1/presets', 'GET', { signal })
  return response.json() as Promise<Preset[]>
}

export async function uploadImage(file: File, signal?: AbortSignal): Promise<UploadedImage> {
  const body = new FormData()
  body.append('file', file)
  const response = await request('/api/v1/images', 'POST', { body, signal })
  return response.json() as Promise<UploadedImage>
}

export async function getOriginalPreview(imageId: string, token: string, signal?: AbortSignal): Promise<Blob> {
  const response = await request(`${imagePath(imageId)}/original-preview`, 'GET', { token, signal })
  return response.blob()
}

export async function getPreview(
  imageId: string,
  token: string,
  revision: number,
  adjustments: Adjustments,
  signal?: AbortSignal,
): Promise<{ blob: Blob; revision: string | null }> {
  const response = await request(`${imagePath(imageId)}/preview`, 'POST', {
    token,
    signal,
    json: { revision, adjustments },
  })
  return { blob: await response.blob(), revision: response.headers.get('X-Image-Revision') }
}

export async function enhanceImage(imageId: string, token: string, signal?: AbortSignal): Promise<Enhancement> {
  const response = await request(`${imagePath(imageId)}/enhance`, 'POST', { token, signal })
  return response.json() as Promise<Enhancement>
}

export async function exportImage(
  imageId: string,
  token: string,
  adjustments: Adjustments,
  signal?: AbortSignal,
): Promise<{ blob: Blob; contentDisposition: string | null }> {
  const response = await request(`${imagePath(imageId)}/export`, 'POST', {
    token,
    signal,
    json: { adjustments, format: 'jpeg', quality: 92 },
  })
  return { blob: await response.blob(), contentDisposition: response.headers.get('Content-Disposition') }
}

export async function deleteImage(imageId: string, token: string, signal?: AbortSignal): Promise<void> {
  await request(imagePath(imageId), 'DELETE', { token, signal })
}
