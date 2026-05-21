from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field

AccuracyPreset = Literal['fast', 'medium', 'high', 'best']
TranscriptionLanguage = Literal['auto', 'en', 'fr']
JobStatus = Literal['queued', 'running', 'completed', 'failed']


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TranscriptSegment(BaseModel):
    start: str
    end: str
    start_seconds: float
    end_seconds: float
    text: str


class JobInfo(BaseModel):
    job_id: str
    status: JobStatus = 'queued'
    original_filename: str
    saved_filename: str
    preset: AccuracyPreset
    language: TranscriptionLanguage
    duration_seconds: float | None = None
    current_seconds: float | None = None
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    estimate_seconds: float | None = None
    detected_language: str | None = None
    language_probability: float | None = None
    error: str | None = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)
    partial_segments: list[TranscriptSegment] = Field(default_factory=list)
    outputs: dict[str, str] = Field(default_factory=dict)


class CreateJobResponse(BaseModel):
    job_id: str
    status_url: str
