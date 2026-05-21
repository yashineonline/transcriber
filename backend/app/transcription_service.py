from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Callable

from .models import TranscriptSegment, TranscriptionLanguage, AccuracyPreset
from .settings import COMPUTE_TYPE, DEVICE


@dataclass(frozen=True)
class WhisperPreset:
    model_size: str
    beam_size: int
    vad_filter: bool
    vad_min_silence_duration_ms: int
    condition_on_previous_text: bool
    temperature: float
    estimated_realtime_factor_cpu: float


PRESETS: dict[AccuracyPreset, WhisperPreset] = {
    'fast': WhisperPreset(
        model_size='small',
        beam_size=1,
        vad_filter=True,
        vad_min_silence_duration_ms=700,
        condition_on_previous_text=False,
        temperature=0.0,
        estimated_realtime_factor_cpu=0.65,
    ),
    'medium': WhisperPreset(
        model_size='medium',
        beam_size=5,
        vad_filter=True,
        vad_min_silence_duration_ms=700,
        condition_on_previous_text=False,
        temperature=0.0,
        estimated_realtime_factor_cpu=1.35,
    ),
    'high': WhisperPreset(
        model_size='large-v3-turbo',
        beam_size=5,
        vad_filter=True,
        vad_min_silence_duration_ms=700,
        condition_on_previous_text=False,
        temperature=0.0,
        estimated_realtime_factor_cpu=2.2,
    ),
    'best': WhisperPreset(
        model_size='large-v3',
        beam_size=7,
        vad_filter=True,
        vad_min_silence_duration_ms=700,
        condition_on_previous_text=False,
        temperature=0.0,
        estimated_realtime_factor_cpu=3.5,
    ),
}

_model_cache: dict[tuple[str, str, str], object] = {}
_model_lock = threading.Lock()


def format_time(seconds: float) -> str:
    td = timedelta(seconds=float(seconds))
    total_seconds = int(td.total_seconds())
    milliseconds = int((float(seconds) - int(float(seconds))) * 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f'{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}'


def estimate_runtime_seconds(duration_seconds: float | None, preset_name: AccuracyPreset) -> float | None:
    if not duration_seconds:
        return None
    preset = PRESETS[preset_name]
    # GPU estimates are intentionally conservative; real performance depends on the GPU.
    factor = preset.estimated_realtime_factor_cpu
    if DEVICE == 'cuda':
        factor *= 0.35
    return max(20.0, duration_seconds * factor)


def get_model(model_size: str):
    from faster_whisper import WhisperModel

    key = (model_size, DEVICE, COMPUTE_TYPE)
    with _model_lock:
        if key not in _model_cache:
            _model_cache[key] = WhisperModel(model_size, device=DEVICE, compute_type=COMPUTE_TYPE)
        return _model_cache[key]


def write_outputs(
    output_dir: Path,
    original_filename: str,
    segments: list[TranscriptSegment],
    detected_language: str | None,
    language_probability: float | None,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    base = Path(original_filename).stem
    timestamped_path = output_dir / f'{base}_timestamped.txt'
    clean_path = output_dir / f'{base}_clean.txt'
    json_path = output_dir / f'{base}_segments.json'

    with timestamped_path.open('w', encoding='utf-8') as handle:
        for seg in segments:
            text = seg.text.strip()
            if text:
                handle.write(f'[{seg.start} --> {seg.end}] {text}\n')

    with clean_path.open('w', encoding='utf-8') as handle:
        for seg in segments:
            text = seg.text.strip()
            if text:
                handle.write(text + '\n')

    with json_path.open('w', encoding='utf-8') as handle:
        json.dump(
            {
                'detected_language': detected_language,
                'language_probability': language_probability,
                'segments': [seg.model_dump() for seg in segments],
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )

    return {
        'timestamped': str(timestamped_path),
        'clean': str(clean_path),
        'json': str(json_path),
    }


def transcribe_file(
    input_path: Path,
    output_dir: Path,
    original_filename: str,
    preset_name: AccuracyPreset,
    language: TranscriptionLanguage,
    duration_hint: float | None,
    progress_callback: Callable[[dict], None],
) -> dict:
    preset = PRESETS[preset_name]
    model = get_model(preset.model_size)
    whisper_language = None if language == 'auto' else language

    vad_parameters = None
    if preset.vad_filter:
        vad_parameters = {'min_silence_duration_ms': preset.vad_min_silence_duration_ms}

    progress_callback({'status': 'running', 'progress': 0.01})

    segments_iter, info = model.transcribe(
        str(input_path),
        language=whisper_language,
        beam_size=preset.beam_size,
        vad_filter=preset.vad_filter,
        vad_parameters=vad_parameters,
        condition_on_previous_text=preset.condition_on_previous_text,
        temperature=preset.temperature,
    )

    duration = duration_hint or getattr(info, 'duration', None)
    progress_callback({
        'duration_seconds': duration,
        'detected_language': getattr(info, 'language', None),
        'language_probability': getattr(info, 'language_probability', None),
    })

    collected: list[TranscriptSegment] = []
    for segment in segments_iter:
        item = TranscriptSegment(
            start=format_time(segment.start),
            end=format_time(segment.end),
            start_seconds=float(segment.start),
            end_seconds=float(segment.end),
            text=segment.text,
        )
        collected.append(item)
        if duration:
            progress = min(0.98, max(0.01, float(segment.end) / float(duration)))
        else:
            progress = min(0.95, 0.01 + len(collected) * 0.01)
        progress_callback({
            'current_seconds': float(segment.end),
            'progress': progress,
            'partial_segments': collected,
        })

    outputs = write_outputs(
        output_dir=output_dir,
        original_filename=original_filename,
        segments=collected,
        detected_language=getattr(info, 'language', None),
        language_probability=getattr(info, 'language_probability', None),
    )

    return {
        'status': 'completed',
        'progress': 1.0,
        'partial_segments': collected,
        'outputs': outputs,
        'duration_seconds': duration,
        'detected_language': getattr(info, 'language', None),
        'language_probability': getattr(info, 'language_probability', None),
    }
