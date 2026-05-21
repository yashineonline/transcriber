from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .jobs import job_store
from .models import AccuracyPreset, CreateJobResponse, TranscriptionLanguage
from .settings import FRONTEND_ORIGIN, MAX_UPLOAD_MB, SUPPORTED_EXTENSIONS
from .transcription_service import PRESETS

app = FastAPI(title='Whisper Transcriber API')

allowed_origins = [origin.strip() for origin in FRONTEND_ORIGIN.split(',') if origin.strip()]
allowed_origins.extend(['http://localhost:5173', 'http://127.0.0.1:5173'])

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(set(allowed_origins)),
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/api/health')
def health() -> dict:
    return {'ok': True}


@app.get('/api/capabilities')
def capabilities() -> dict:
    return {
        'supported_extensions': sorted(SUPPORTED_EXTENSIONS),
        'presets': {
            name: {
                'model_size': preset.model_size,
                'beam_size': preset.beam_size,
                'vad_filter': preset.vad_filter,
                'estimated_realtime_factor_cpu': preset.estimated_realtime_factor_cpu,
            }
            for name, preset in PRESETS.items()
        },
        'languages': ['auto', 'en', 'fr'],
        'max_upload_mb': MAX_UPLOAD_MB,
    }


@app.post('/api/jobs', response_model=CreateJobResponse)
async def create_job(
    file: UploadFile = File(...),
    preset: AccuracyPreset = Form('medium'),
    language: TranscriptionLanguage = Form('auto'),
    duration_seconds: float | None = Form(None),
) -> CreateJobResponse:
    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f'Unsupported file type: {suffix or "unknown"}')

    try:
        job = await job_store.create(file, preset=preset, language=language, duration_seconds=duration_seconds)
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    return CreateJobResponse(job_id=job.job_id, status_url=f'/api/jobs/{job.job_id}')


@app.get('/api/jobs/{job_id}')
def get_job(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    data = job.model_dump()
    # Do not expose internal server paths.
    data['outputs'] = {kind: f'/api/jobs/{job_id}/download?kind={kind}' for kind in job.outputs}
    return data


@app.get('/api/jobs/{job_id}/download')
def download_job(job_id: str, kind: str = 'timestamped'):
    if kind not in {'timestamped', 'clean', 'json'}:
        raise HTTPException(status_code=400, detail='kind must be timestamped, clean, or json')

    path = job_store.output_path(job_id, kind)
    if not path:
        raise HTTPException(status_code=404, detail='Transcript not ready or not found')

    media_type = 'application/json' if kind == 'json' else 'text/plain; charset=utf-8'
    return FileResponse(path, media_type=media_type, filename=path.name)
