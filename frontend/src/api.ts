import type { AccuracyPreset, CreateJobResponse, JobInfo, TranscriptionLanguage } from './types'

const API_BASE = import.meta.env.VITE_API_BASE || ''

function apiUrl(path: string): string {
  if (!API_BASE) return path
  return `${API_BASE}${path}`
}

export async function createTranscriptionJob(params: {
  file: File
  language: TranscriptionLanguage
  preset: AccuracyPreset
  durationSeconds?: number | null
}): Promise<CreateJobResponse> {
  const form = new FormData()
  form.append('file', params.file)
  form.append('language', params.language)
  form.append('preset', params.preset)
  if (params.durationSeconds) form.append('duration_seconds', String(params.durationSeconds))

  const response = await fetch(apiUrl('/api/jobs'), {
    method: 'POST',
    body: form
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Upload failed with status ${response.status}`)
  }

  return response.json()
}

export async function getJob(jobId: string): Promise<JobInfo> {
  const response = await fetch(apiUrl(`/api/jobs/${jobId}`))
  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Could not load job ${jobId}`)
  }
  return response.json()
}

export async function downloadTranscript(jobId: string, kind: 'timestamped' | 'clean' | 'json'): Promise<Blob> {
  const response = await fetch(apiUrl(`/api/jobs/${jobId}/download?kind=${kind}`))
  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Could not download ${kind} transcript`)
  }
  return response.blob()
}

export function downloadUrl(jobId: string, kind: 'timestamped' | 'clean' | 'json'): string {
  return apiUrl(`/api/jobs/${jobId}/download?kind=${kind}`)
}
