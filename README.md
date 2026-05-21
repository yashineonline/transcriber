# Whisper Transcriber PWA

A Vite + Vue 3 + TypeScript + Tailwind + daisyUI Progressive Web App for uploading audio/video recordings and transcribing them through a Python `faster-whisper` backend.

This repository is designed for people to use the interface from a phone, iPhone, iPad, tablet, or desktop browser. The transcription itself runs on the backend server because iOS/Android browsers cannot run the Python Whisper script directly inside the PWA.

## What is included

- `frontend/`: Vite Vue 3 TypeScript PWA interface.
- `backend/`: FastAPI backend using `faster-whisper`, adapted from the original standalone Python script.
- `.github/workflows/basic-ci.yml`: checks frontend build and backend Python syntax.
- `.devcontainer/devcontainer.json`: GitHub Codespaces / VS Code container setup.
- `docker-compose.yml`: local full-stack launch.
- `DISCUSSION_AND_LIMITATIONS.md`: important design notes and limitations before publishing.

## Features

- Upload common audio/video formats: `.mp3`, `.mp4`, `.m4a`, `.wav`, `.aac`, `.flac`, `.ogg`, `.webm`, `.mov`.
- Choose transcription language: auto-detect, English, or French.
- Choose accuracy/speed preset: Fast, Medium, High, Best.
- Shows approximate transcription time based on recording length and selected preset.
- Keeps a server-side job running after upload, so the user can leave the PWA and come back later.
- Saves/resumes the current job ID in browser local storage.
- Downloads timestamped transcript, clean transcript, or JSON segment data.
- Uses File System Access API when available to let the user choose a save folder; falls back to normal browser downloads when unsupported.
- Installable PWA with app icon and manifest.

## Important architecture note

A static GitHub Pages site alone is not enough for this project because the transcription code is Python and uses `faster-whisper`. GitHub Pages can host the frontend, but the Python backend must run somewhere else, for example:

- your own server,
- a university server,
- a cloud VM,
- Render/Fly.io/Railway/Azure/GCP/AWS,
- or locally through Docker/Codespaces for testing.

## Quick start with Docker

From the repository root:

```bash
docker compose up --build
```

Open:

```text
http://localhost:5173
```

The backend will run at:

```text
http://localhost:8000
```

The first transcription may be slow because the Whisper model must be downloaded.

## Manual local setup

### 1. Backend

Install Python 3.11+ and then:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend

Install Node.js 22+ and then:

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

Open the local URL shown by Vite, usually:

```text
http://localhost:5173
```

## Environment variables

Backend variables:

```bash
TRANSCRIBE_DEVICE=cpu              # cpu or cuda
TRANSCRIBE_COMPUTE_TYPE=int8       # int8 for CPU, float16 for CUDA
TRANSCRIBE_WORKERS=1               # number of simultaneous jobs
TRANSCRIBE_DATA_DIR=.data          # where uploads/jobs/outputs are stored
FRONTEND_ORIGIN=http://localhost:5173
```

Frontend variables:

Create `frontend/.env.local`:

```bash
VITE_API_BASE=http://localhost:8000
```

For Vite development, the repo already proxies `/api` to `localhost:8000`, so `VITE_API_BASE` can usually stay empty.

## GitHub Actions

The included workflow checks that:

1. the frontend installs and builds,
2. the backend Python files compile syntactically.

When you first run `npm install` inside `frontend/`, commit the generated `package-lock.json` if you want reproducible CI installs. The current workflow uses `npm install` so it will still run without an initial lock file.

## GitHub Codespaces

This repo includes a `.devcontainer/devcontainer.json`. In GitHub:

1. Click **Code**.
2. Click **Codespaces**.
3. Create a codespace.
4. Run:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend
```

In another terminal:

```bash
cd frontend
npm run dev -- --host 0.0.0.0
```

Codespaces will forward ports 5173 and 8000.

## Deployment options

### Option A: one server for both frontend and backend

Build the frontend:

```bash
cd frontend
npm install
npm run build
```

Then serve `frontend/dist` with Nginx/Caddy and proxy `/api` to the FastAPI backend.

### Option B: GitHub Pages frontend + hosted backend

1. Host the frontend on GitHub Pages or another static host.
2. Host the backend on a Python-capable server.
3. Set `VITE_API_BASE=https://your-backend.example.com` before building the frontend.
4. Set `FRONTEND_ORIGIN=https://your-github-pages-url` on the backend.

## Privacy note

Uploaded audio/video is stored on the backend while the job runs. For a public service, add authentication, file-size limits, automatic cleanup, HTTPS, and a clear data-retention notice before letting others use it.
