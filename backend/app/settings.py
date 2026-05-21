from __future__ import annotations

import os
from pathlib import Path

SUPPORTED_EXTENSIONS = {'.mp3', '.mp4', '.m4a', '.wav', '.aac', '.flac', '.ogg', '.webm', '.mov'}

DATA_DIR = Path(os.getenv('TRANSCRIBE_DATA_DIR', Path(__file__).resolve().parents[1] / '.data'))
UPLOAD_DIR = DATA_DIR / 'uploads'
OUTPUT_DIR = DATA_DIR / 'outputs'
JOBS_FILE = DATA_DIR / 'jobs.json'

DEVICE = os.getenv('TRANSCRIBE_DEVICE', 'cpu')
COMPUTE_TYPE = os.getenv('TRANSCRIBE_COMPUTE_TYPE', 'int8')
WORKERS = int(os.getenv('TRANSCRIBE_WORKERS', '1'))
FRONTEND_ORIGIN = os.getenv('FRONTEND_ORIGIN', 'http://localhost:5173')
MAX_UPLOAD_MB = int(os.getenv('MAX_UPLOAD_MB', '2048'))

for directory in (DATA_DIR, UPLOAD_DIR, OUTPUT_DIR):
    directory.mkdir(parents=True, exist_ok=True)
