<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { createTranscriptionJob, downloadTranscript, getJob } from './api'
import type { AccuracyPreset, JobInfo, TranscriptionLanguage, UiLanguage } from './types'
import { estimateSeconds, formatDuration, getMediaDuration, safeBaseName, saveBlob } from './utils'

const STORAGE_KEY = 'whisper-transcriber:last-job-id'

const uiLanguage = ref<UiLanguage>('en')
const selectedFile = ref<File | null>(null)
const mediaDuration = ref<number | null>(null)
const transcriptionLanguage = ref<TranscriptionLanguage>('auto')
const preset = ref<AccuracyPreset>('medium')
const directoryHandle = ref<FileSystemDirectoryHandle | null>(null)
const directoryName = ref<string>('')
const job = ref<JobInfo | null>(null)
const busy = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
let poller: number | undefined

const t = computed(() => {
  const en = {
    title: 'Y Transcribe',
    subtitle: 'Upload an audio or video file, choose the language and accuracy, then come back when the transcript is ready.',
    uiLanguage: 'Interface',
    upload: 'Recording',
    chooseFile: 'Choose audio/video file',
    language: 'Transcription language',
    auto: 'Auto-detect',
    english: 'English',
    french: 'French',
    accuracy: 'Accuracy',
    fast: 'Fast',
    medium: 'Medium',
    high: 'High',
    best: 'Best',
    fastDesc: 'quick rough transcript',
    mediumDesc: 'recommended balance',
    highDesc: 'more accurate, slower',
    bestDesc: 'highest quality, slowest',
    duration: 'Recording length',
    estimate: 'Estimated transcription time',
    estimateNote: 'Approximate; depends on CPU/GPU, server load, audio quality, and upload speed.',
    chooseFolder: 'Choose save folder',
    folderUnsupported: 'Folder access is not supported in this browser. Normal download buttons will be used.',
    folderChosen: 'Save folder',
    start: 'Upload and transcribe',
    resume: 'Resuming previous job',
    status: 'Status',
    progress: 'Progress',
    detected: 'Detected language',
    transcript: 'Transcript preview',
    timestamped: 'Save timestamped .txt',
    clean: 'Save clean .txt',
    json: 'Save .json segments',
    noTranscript: 'Transcript preview will appear as segments are processed.',
    privacy: 'Privacy reminder: recordings are uploaded to the backend server for transcription.',
    install: 'Install this app from your browser menu for a phone/tablet-like experience.'
  }
  const fr = {
    title: 'Transcription Whisper',
    subtitle: 'Téléversez un fichier audio ou vidéo, choisissez la langue et la précision, puis revenez quand la transcription est prête.',
    uiLanguage: 'Interface',
    upload: 'Enregistrement',
    chooseFile: 'Choisir un fichier audio/vidéo',
    language: 'Langue de transcription',
    auto: 'Détection automatique',
    english: 'Anglais',
    french: 'Français',
    accuracy: 'Précision',
    fast: 'Rapide',
    medium: 'Moyenne',
    high: 'Élevée',
    best: 'Maximale',
    fastDesc: 'brouillon rapide',
    mediumDesc: 'équilibre recommandé',
    highDesc: 'plus précis, plus lent',
    bestDesc: 'meilleure qualité, plus lent',
    duration: 'Durée de l’enregistrement',
    estimate: 'Temps estimé de transcription',
    estimateNote: 'Approximation; dépend du CPU/GPU, du serveur, de la qualité audio et de l’envoi du fichier.',
    chooseFolder: 'Choisir le dossier de sauvegarde',
    folderUnsupported: 'Le choix du dossier n’est pas pris en charge dans ce navigateur. Les boutons de téléchargement seront utilisés.',
    folderChosen: 'Dossier de sauvegarde',
    start: 'Téléverser et transcrire',
    resume: 'Reprise de la tâche précédente',
    status: 'Statut',
    progress: 'Progression',
    detected: 'Langue détectée',
    transcript: 'Aperçu de la transcription',
    timestamped: 'Sauver .txt avec minutage',
    clean: 'Sauver .txt propre',
    json: 'Sauver segments .json',
    noTranscript: 'L’aperçu apparaîtra pendant le traitement des segments.',
    privacy: 'Confidentialité : les enregistrements sont envoyés au serveur backend pour transcription.',
    install: 'Installez cette app depuis le menu du navigateur pour une expérience téléphone/tablette.'
  }
  return uiLanguage.value === 'fr' ? fr : en
})

const estimate = computed(() => estimateSeconds(mediaDuration.value, preset.value))
const canUseDirectoryPicker = computed(() => typeof window.showDirectoryPicker === 'function')
const canStart = computed(() => selectedFile.value && !busy.value)
const progressPercent = computed(() => Math.round((job.value?.progress ?? 0) * 100))
const baseName = computed(() => selectedFile.value ? safeBaseName(selectedFile.value.name) : (job.value ? safeBaseName(job.value.original_filename) : 'transcript'))
const transcriptText = computed(() => (job.value?.partial_segments ?? []).map((seg) => `[${seg.start} → ${seg.end}] ${seg.text.trim()}`).join('\n'))

const presetCards = computed(() => [
  { key: 'fast' as const, label: t.value.fast, desc: t.value.fastDesc },
  { key: 'medium' as const, label: t.value.medium, desc: t.value.mediumDesc },
  { key: 'high' as const, label: t.value.high, desc: t.value.highDesc },
  { key: 'best' as const, label: t.value.best, desc: t.value.bestDesc }
])

watch(selectedFile, async (file) => {
  mediaDuration.value = null
  errorMessage.value = ''
  if (file) mediaDuration.value = await getMediaDuration(file)
})

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
}

async function chooseFolder() {
  errorMessage.value = ''
  successMessage.value = ''
  if (!window.showDirectoryPicker) return
  try {
    directoryHandle.value = await window.showDirectoryPicker({ mode: 'readwrite' })
    directoryName.value = directoryHandle.value.name
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') return
    errorMessage.value = error instanceof Error ? error.message : String(error)
  }
}

async function startJob() {
  if (!selectedFile.value) return
  busy.value = true
  errorMessage.value = ''
  successMessage.value = ''
  job.value = null
  try {
    const created = await createTranscriptionJob({
      file: selectedFile.value,
      language: transcriptionLanguage.value,
      preset: preset.value,
      durationSeconds: mediaDuration.value
    })
    localStorage.setItem(STORAGE_KEY, created.job_id)
    await pollJob(created.job_id)
    startPolling(created.job_id)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    busy.value = false
  }
}

async function pollJob(jobId: string) {
  try {
    job.value = await getJob(jobId)
    if (job.value.status === 'completed' || job.value.status === 'failed') {
      stopPolling()
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
    stopPolling()
  }
}

function startPolling(jobId: string) {
  stopPolling()
  poller = window.setInterval(() => pollJob(jobId), 2500)
}

function stopPolling() {
  if (poller) window.clearInterval(poller)
  poller = undefined
}

async function save(kind: 'timestamped' | 'clean' | 'json') {
  if (!job.value) return
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const blob = await downloadTranscript(job.value.job_id, kind)
    const extension = kind === 'json' ? 'json' : 'txt'
    const suffix = kind === 'timestamped' ? 'timestamped' : kind
    const result = await saveBlob({
      blob,
      filename: `${baseName.value}_${suffix}.${extension}`,
      directoryHandle: directoryHandle.value
    })
    successMessage.value = result === 'directory'
      ? `Saved to ${directoryName.value || 'selected folder'}.`
      : 'Download started.'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  }
}

onMounted(async () => {
  const lastJob = localStorage.getItem(STORAGE_KEY)
  if (lastJob) {
    successMessage.value = t.value.resume
    await pollJob(lastJob)
    if (job.value && (job.value.status === 'queued' || job.value.status === 'running')) {
      startPolling(lastJob)
    }
  }
})

onBeforeUnmount(stopPolling)
</script>

<template>
  <main class="min-h-screen bg-base-200 text-base-content">
    <section class="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-6 md:py-10">
      <div class="hero rounded-3xl bg-base-100 shadow-xl">
        <div class="hero-content flex-col gap-6 py-8 text-center md:py-12">
          <img src="/pwa-192x192.png" alt="" class="h-20 w-20 rounded-3xl shadow-md" />
          <div>
            <h1 class="text-4xl font-bold tracking-tight md:text-5xl">{{ t.title }}</h1>
            <p class="mx-auto mt-4 max-w-2xl text-base opacity-80 md:text-lg">{{ t.subtitle }}</p>
          </div>
          <div class="join">
            <button class="btn join-item" :class="uiLanguage === 'en' ? 'btn-primary' : 'btn-ghost'" @click="uiLanguage = 'en'">EN</button>
            <button class="btn join-item" :class="uiLanguage === 'fr' ? 'btn-primary' : 'btn-ghost'" @click="uiLanguage = 'fr'">FR</button>
          </div>
        </div>
      </div>

      <div v-if="errorMessage" class="alert alert-error shadow">
        <span>{{ errorMessage }}</span>
      </div>
      <div v-if="successMessage" class="alert alert-success shadow">
        <span>{{ successMessage }}</span>
      </div>

      <div class="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <section class="card bg-base-100 shadow-xl">
          <div class="card-body gap-5">
            <h2 class="card-title text-2xl">{{ t.upload }}</h2>

            <label class="form-control w-full">
              <div class="label"><span class="label-text font-medium">{{ t.chooseFile }}</span></div>
              <input class="file-input file-input-bordered file-input-primary w-full" type="file" accept="audio/*,video/*,.mp3,.mp4,.m4a,.wav,.aac,.flac,.ogg,.webm,.mov" @change="onFileChange" />
            </label>

            <div class="grid gap-4 md:grid-cols-2">
              <label class="form-control w-full">
                <div class="label"><span class="label-text font-medium">{{ t.language }}</span></div>
                <select v-model="transcriptionLanguage" class="select select-bordered w-full">
                  <option value="auto">{{ t.auto }}</option>
                  <option value="en">{{ t.english }}</option>
                  <option value="fr">{{ t.french }}</option>
                </select>
              </label>

              <div class="rounded-2xl bg-base-200 p-4">
                <div class="text-sm opacity-70">{{ t.duration }}</div>
                <div class="mt-1 text-2xl font-semibold">{{ formatDuration(mediaDuration) }}</div>
              </div>
            </div>

            <div>
              <div class="mb-2 font-medium">{{ t.accuracy }}</div>
              <div class="grid gap-3 md:grid-cols-2">
                <label v-for="item in presetCards" :key="item.key" class="cursor-pointer rounded-2xl border p-4 transition hover:border-primary" :class="preset === item.key ? 'border-primary bg-primary/10' : 'border-base-300 bg-base-100'">
                  <input v-model="preset" class="radio radio-primary mr-2" type="radio" name="preset" :value="item.key" />
                  <span class="font-semibold">{{ item.label }}</span>
                  <p class="mt-1 text-sm opacity-70">{{ item.desc }}</p>
                </label>
              </div>
            </div>

            <div class="stats stats-vertical bg-base-200 shadow md:stats-horizontal">
              <div class="stat">
                <div class="stat-title">{{ t.estimate }}</div>
                <div class="stat-value text-primary">{{ formatDuration(estimate) }}</div>
                <div class="stat-desc whitespace-normal">{{ t.estimateNote }}</div>
              </div>
            </div>

            <div class="rounded-2xl border border-base-300 p-4">
              <button v-if="canUseDirectoryPicker" type="button" class="btn btn-outline btn-primary" @click="chooseFolder">
                {{ t.chooseFolder }}
              </button>
              <p v-else class="text-sm opacity-70">{{ t.folderUnsupported }}</p>
              <p v-if="directoryName" class="mt-2 text-sm"><strong>{{ t.folderChosen }}:</strong> {{ directoryName }}</p>
            </div>

            <button class="btn btn-primary btn-lg" :disabled="!canStart" @click="startJob">
              <span v-if="busy" class="loading loading-spinner"></span>
              {{ t.start }}
            </button>

            <p class="text-sm opacity-70">{{ t.privacy }}</p>
            <p class="text-sm opacity-70">{{ t.install }}</p>
          </div>
        </section>

        <section class="card bg-base-100 shadow-xl">
          <div class="card-body gap-5">
            <h2 class="card-title text-2xl">{{ t.status }}</h2>

            <div v-if="job" class="space-y-4">
              <div class="flex flex-wrap items-center gap-2">
                <div class="badge badge-lg" :class="{
                  'badge-info': job.status === 'queued',
                  'badge-warning': job.status === 'running',
                  'badge-success': job.status === 'completed',
                  'badge-error': job.status === 'failed'
                }">{{ job.status }}</div>
                <span class="text-sm opacity-70">{{ job.original_filename }}</span>
              </div>

              <div>
                <div class="mb-1 flex justify-between text-sm">
                  <span>{{ t.progress }}</span>
                  <span>{{ progressPercent }}%</span>
                </div>
                <progress class="progress progress-primary w-full" :value="progressPercent" max="100"></progress>
              </div>

              <div class="grid gap-3 md:grid-cols-2">
                <div class="rounded-2xl bg-base-200 p-4">
                  <div class="text-sm opacity-70">{{ t.duration }}</div>
                  <div class="font-semibold">{{ formatDuration(job.duration_seconds) }}</div>
                </div>
                <div class="rounded-2xl bg-base-200 p-4">
                  <div class="text-sm opacity-70">{{ t.detected }}</div>
                  <div class="font-semibold">{{ job.detected_language || '—' }}</div>
                </div>
              </div>

              <div v-if="job.status === 'completed'" class="grid gap-3">
                <button class="btn btn-success" @click="save('timestamped')">{{ t.timestamped }}</button>
                <button class="btn btn-outline" @click="save('clean')">{{ t.clean }}</button>
                <button class="btn btn-outline" @click="save('json')">{{ t.json }}</button>
              </div>

              <div v-if="job.error" class="alert alert-error"><span>{{ job.error }}</span></div>
            </div>

            <div v-else class="rounded-2xl bg-base-200 p-5 text-sm opacity-70">
              {{ t.noTranscript }}
            </div>
          </div>
        </section>
      </div>

      <section class="card bg-base-100 shadow-xl">
        <div class="card-body">
          <h2 class="card-title text-2xl">{{ t.transcript }}</h2>
          <textarea class="textarea textarea-bordered min-h-72 w-full font-mono text-sm" readonly :value="transcriptText || t.noTranscript"></textarea>
        </div>
      </section>
    </section>
  </main>
</template>
