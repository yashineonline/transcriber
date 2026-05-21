#!/usr/bin/env python3
"""
Adjusted standalone CLI version of the original script.

This can still be used locally without the web app:

    python -m app.transcribe_audio_video_adjusted --input lecture.mp4 --preset high --language fr

For the web app, the backend imports transcription_service.py instead.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .transcription_service import PRESETS, transcribe_file


def main() -> None:
    parser = argparse.ArgumentParser(description='Transcribe audio/video using faster-whisper presets.')
    parser.add_argument('--input', required=True, help='Audio/video file to transcribe')
    parser.add_argument('--output-dir', default='.', help='Folder for transcript outputs')
    parser.add_argument('--preset', choices=sorted(PRESETS.keys()), default='medium')
    parser.add_argument('--language', choices=['auto', 'en', 'fr'], default='auto')
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    def progress(update: dict) -> None:
        if 'progress' in update:
            print(f"Progress: {update['progress'] * 100:.1f}%")

    result = transcribe_file(
        input_path=input_path,
        output_dir=output_dir,
        original_filename=input_path.name,
        preset_name=args.preset,
        language=args.language,
        duration_hint=None,
        progress_callback=progress,
    )
    print('Done')
    print(result['outputs'])


if __name__ == '__main__':
    main()
