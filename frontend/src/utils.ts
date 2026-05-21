import type { AccuracyPreset } from './types'

const ESTIMATE_FACTORS: Record<AccuracyPreset, number> = {
  fast: 0.65,
  medium: 1.35,
  high: 2.2,
  best: 3.5
}

export function formatDuration(seconds?: number | null): string {
  if (!seconds || !Number.isFinite(seconds)) return '—'
  const rounded = Math.max(0, Math.round(seconds))
  const h = Math.floor(rounded / 3600)
  const m = Math.floor((rounded % 3600) / 60)
  const s = rounded % 60
  if (h > 0) return `${h}h ${m}m ${s}s`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

export function estimateSeconds(durationSeconds: number | null, preset: AccuracyPreset): number | null {
  if (!durationSeconds || !Number.isFinite(durationSeconds)) return null
  return Math.max(20, durationSeconds * ESTIMATE_FACTORS[preset])
}

export async function getMediaDuration(file: File): Promise<number | null> {
  const url = URL.createObjectURL(file)
  const media = document.createElement(file.type.startsWith('video/') ? 'video' : 'audio')
  media.preload = 'metadata'

  return new Promise((resolve) => {
    const cleanup = () => URL.revokeObjectURL(url)
    media.onloadedmetadata = () => {
      const duration = Number.isFinite(media.duration) ? media.duration : null
      cleanup()
      resolve(duration)
    }
    media.onerror = () => {
      cleanup()
      resolve(null)
    }
    media.src = url
  })
}

export function safeBaseName(filename: string): string {
  return filename.replace(/\.[^/.]+$/, '').replace(/[^a-z0-9._-]+/gi, '_')
}

export async function saveBlob(params: {
  blob: Blob
  filename: string
  directoryHandle: FileSystemDirectoryHandle | null
}): Promise<'directory' | 'download'> {
  if (params.directoryHandle) {
    const permission = params.directoryHandle.queryPermission
      ? await params.directoryHandle.queryPermission({ mode: 'readwrite' })
      : 'granted'

    let finalPermission = permission
    if (permission !== 'granted' && params.directoryHandle.requestPermission) {
      finalPermission = await params.directoryHandle.requestPermission({ mode: 'readwrite' })
    }

    if (finalPermission === 'granted') {
      const fileHandle = await params.directoryHandle.getFileHandle(params.filename, { create: true })
      const writable = await fileHandle.createWritable()
      await writable.write(params.blob)
      await writable.close()
      return 'directory'
    }
  }

  const url = URL.createObjectURL(params.blob)
  const a = document.createElement('a')
  a.href = url
  a.download = params.filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
  return 'download'
}
