from __future__ import annotations

import json
import shutil
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock

from fastapi import UploadFile

from .models import AccuracyPreset, JobInfo, TranscriptionLanguage, now_iso
from .settings import JOBS_FILE, MAX_UPLOAD_MB, OUTPUT_DIR, UPLOAD_DIR, WORKERS
from .transcription_service import estimate_runtime_seconds, transcribe_file


class JobStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._jobs: dict[str, JobInfo] = {}
        self._executor = ThreadPoolExecutor(max_workers=WORKERS)
        self._load()
        self._mark_interrupted_jobs_failed()

    def _load(self) -> None:
        if not JOBS_FILE.exists():
            return
        try:
            data = json.loads(JOBS_FILE.read_text(encoding='utf-8'))
            self._jobs = {job_id: JobInfo.model_validate(item) for job_id, item in data.items()}
        except Exception:
            self._jobs = {}

    def _save(self) -> None:
        JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
        serializable = {job_id: job.model_dump() for job_id, job in self._jobs.items()}
        JOBS_FILE.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding='utf-8')

    def _mark_interrupted_jobs_failed(self) -> None:
        changed = False
        for job in self._jobs.values():
            if job.status in {'queued', 'running'}:
                job.status = 'failed'
                job.error = 'Backend restarted before this job completed. Please upload again.'
                job.updated_at = now_iso()
                changed = True
        if changed:
            self._save()

    def get(self, job_id: str) -> JobInfo | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **changes) -> None:
        with self._lock:
            job = self._jobs[job_id]
            for key, value in changes.items():
                setattr(job, key, value)
            job.updated_at = now_iso()
            self._save()

    async def create(self, upload: UploadFile, preset: AccuracyPreset, language: TranscriptionLanguage, duration_seconds: float | None) -> JobInfo:
        job_id = uuid.uuid4().hex
        suffix = Path(upload.filename or 'recording').suffix.lower() or '.bin'
        saved_filename = f'{job_id}{suffix}'
        saved_path = UPLOAD_DIR / saved_filename

        max_bytes = MAX_UPLOAD_MB * 1024 * 1024
        written = 0
        with saved_path.open('wb') as handle:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    saved_path.unlink(missing_ok=True)
                    raise ValueError(f'Upload exceeds MAX_UPLOAD_MB={MAX_UPLOAD_MB}')
                handle.write(chunk)

        job = JobInfo(
            job_id=job_id,
            original_filename=upload.filename or saved_filename,
            saved_filename=saved_filename,
            preset=preset,
            language=language,
            duration_seconds=duration_seconds,
            estimate_seconds=estimate_runtime_seconds(duration_seconds, preset),
        )

        with self._lock:
            self._jobs[job_id] = job
            self._save()

        self._executor.submit(self._run_job, job_id, saved_path)
        return job

    def _run_job(self, job_id: str, saved_path: Path) -> None:
        job = self.get(job_id)
        if not job:
            return
        output_dir = OUTPUT_DIR / job_id
        try:
            def progress_callback(changes: dict) -> None:
                self.update(job_id, **changes)

            result = transcribe_file(
                input_path=saved_path,
                output_dir=output_dir,
                original_filename=job.original_filename,
                preset_name=job.preset,
                language=job.language,
                duration_hint=job.duration_seconds,
                progress_callback=progress_callback,
            )
            self.update(job_id, **result)
        except Exception as exc:
            self.update(job_id, status='failed', error=f'{exc}\n\n{traceback.format_exc()}', progress=0.0)

    def output_path(self, job_id: str, kind: str) -> Path | None:
        job = self.get(job_id)
        if not job or kind not in job.outputs:
            return None
        path = Path(job.outputs[kind])
        return path if path.exists() else None


job_store = JobStore()
