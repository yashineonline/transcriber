export type UiLanguage = 'en' | 'fr'
export type TranscriptionLanguage = 'auto' | 'en' | 'fr'
export type AccuracyPreset = 'fast' | 'medium' | 'high' | 'best'
export type JobStatus = 'queued' | 'running' | 'completed' | 'failed'

export interface TranscriptSegment {
  start: string
  end: string
  start_seconds: number
  end_seconds: number
  text: string
}

export interface JobInfo {
  job_id: string
  status: JobStatus
  original_filename: string
  preset: AccuracyPreset
  language: TranscriptionLanguage
  duration_seconds?: number | null
  current_seconds?: number | null
  progress: number
  estimate_seconds?: number | null
  detected_language?: string | null
  language_probability?: number | null
  error?: string | null
  created_at: string
  updated_at: string
  partial_segments: TranscriptSegment[]
  outputs: Record<string, string>
}

export interface CreateJobResponse {
  job_id: string
  status_url: string
}
