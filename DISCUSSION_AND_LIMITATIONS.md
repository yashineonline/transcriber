# Discussion and design choices

## Why the app has a backend

The original script is a local Python script using `faster-whisper`. A Vite/Vue PWA is JavaScript running inside a browser. iPhone, iPad, Android, and desktop browsers do not execute arbitrary Python scripts from a web page. Therefore, this repo uses:

- Vue/Vite PWA for the user interface.
- FastAPI Python backend for transcription.

The PWA can be installed on phones/tablets/desktops, but the actual Whisper computation runs on the backend server.

## Accuracy presets

The interface exposes simple presets instead of making users choose technical Whisper parameters.

| Preset | Model | Beam size | Best use |
|---|---:|---:|---|
| Fast | `small` | 1 | quick rough transcripts |
| Medium | `medium` | 5 | default balance |
| High | `large-v3-turbo` | 5 | better quality, still practical |
| Best | `large-v3` | 7 | highest quality, slowest |

These presets are in `backend/app/transcription_service.py`. You can adjust them depending on your server resources.

## English and French

The frontend lets users choose:

- Auto-detect,
- English,
- French.

The UI itself also has a basic English/French switch. This is intentionally simple and can later be replaced by `vue-i18n` if you want a fully translated app.

## Time estimates

The app estimates the transcription time from the media duration and preset. This is only approximate. Actual speed depends strongly on:

- CPU versus GPU,
- server load,
- Whisper model size,
- recording quality,
- silence/noise,
- upload speed.

The backend also updates progress using the last completed Whisper segment time.

## Leaving the app and coming back

After upload, the transcription job runs on the backend. The browser stores the job ID in local storage. If the user leaves the app and later comes back, the PWA checks the last job ID and resumes polling.

This is not the same as true background processing inside the phone browser. The phone does not keep transcribing locally; the backend does.

## Saving files to phone or desktop

The frontend tries to use the File System Access API for a pre-selected save folder when the browser supports it. Not all browsers support folder-picking. In unsupported browsers, especially iOS Safari, the app falls back to a normal download button.

For production, test saving behavior on:

- iPhone Safari,
- iPad Safari,
- Android Chrome,
- desktop Chrome/Edge,
- desktop Safari,
- desktop Firefox.

## PWA limits

A PWA can be installable and cache the app shell, but this app cannot do full offline transcription because Whisper runs on the backend. Offline support here means the interface shell can load; uploading/transcribing requires network access.

## Recommended production improvements

Before releasing publicly, consider adding:

1. User accounts or access tokens.
2. File size and duration limits.
3. Automatic cleanup of uploads and transcripts.
4. HTTPS-only hosting.
5. Queue system such as Redis Queue, Celery, Dramatiq, or Arq.
6. Persistent database instead of JSON job storage.
7. Email/push notification when transcription is complete.
8. Optional speaker diarization.
9. Optional subtitle export: `.srt` and `.vtt`.
10. Clear privacy/data-retention policy.

## Suggested next feature

Add a “meeting mode” with:

- speaker labels,
- summary,
- action items,
- searchable transcript,
- export to Markdown, DOCX, SRT, and VTT.
