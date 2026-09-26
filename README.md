# Quizzly Backend

**A Django REST API that generates quizzes from YouTube videos.**

> **Educational project:** Developed by Marc-André Buck as part of the Developer Akademie backend training program. This repository contains the independently developed backend for the frontend provided by Developer Akademie. It is a training project, not a production deployment.

**Backend repository:** https://github.com/MarcAndreBuck/quizzly_backend
**Developer Akademie frontend:** https://github.com/Developer-Akademie-Backendkurs/project.Quizly

## Features

- User registration, login, logout, and JWT refresh using HTTP-only cookies.
- User-specific quiz listing, retrieval, partial updates, and deletion.
- Quiz generation from YouTube videos: `yt-dlp` and FFmpeg extract audio, local OpenAI Whisper transcribes it, and Google Gemini Flash generates a title, description, and ten questions with four answer options each.
- Validation of generated quiz data before saving.
- Django admin interface for project administration.

The frontend and backend are separate projects that communicate through the documented REST API.

## Technology stack

| Area | Technology |
| --- | --- |
| Backend | Python 3.12, Django 5.2, Django REST Framework |
| Authentication | Simple JWT, HTTP-only cookies |
| Local database | SQLite |
| Video and audio | `yt-dlp`, FFmpeg |
| Transcription | OpenAI Whisper (`base` model) |
| Quiz generation | Google Gemini Flash through `google-genai` |
| Configuration | `python-dotenv`, `django-cors-headers` |
| Testing | Django test runner, `coverage` |

Exact Python package versions are pinned in [`requirements.txt`](requirements.txt).

## Prerequisites

- Python **3.12** and Git.
- **FFmpeg installed globally and available on your system `PATH`.** This is required for audio processing and Whisper. FFmpeg is a system dependency and is **not** installed by `pip install -r requirements.txt`. Verify it with `ffmpeg -version`.
- A Google Gemini API key.
- An internet connection for YouTube, Gemini, package installation, and the first Whisper model download.
- Disk space for Python dependencies, the Whisper model, and temporary audio processing.

Whisper runs locally. Its `base` model is downloaded on first use and cached for subsequent requests. Processing time depends on the video length and available hardware.

## Installation

### 1. Clone the backend

```bash
git clone https://github.com/MarcAndreBuck/quizzly_backend.git
cd quizzly_backend
```

### 2. Create and activate a virtual environment

**Windows PowerShell**

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3.12 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

If PyTorch or Whisper installation fails on your platform, consult their platform-specific installation instructions. FFmpeg must still be installed separately.

### 4. Configure environment variables

Copy the included `.env.example` to `.env` in the directory containing `manage.py`.

**Windows PowerShell**

```powershell
Copy-Item .env.example .env
```

**macOS / Linux**

```bash
cp .env.example .env
```

Set your own credentials:

```dotenv
DJANGO_SECRET_KEY=replace-with-your-own-unique-django-secret-key
GEMINI_API_KEY=replace-with-your-own-gemini-api-key
```

Generate a unique Django secret key and obtain a Gemini API key. The Gemini client reads `GEMINI_API_KEY` from the environment. **Never commit `.env` or real credentials.** The `.gitignore` excludes `.env`.

### 5. Initialize the database

```bash
python manage.py migrate
```

Optionally create an account for the Django admin interface:

```bash
python manage.py createsuperuser
```

### 6. Run the backend

```bash
python manage.py runserver
```

The local backend is available at `http://127.0.0.1:8000/`; Django admin is at `http://127.0.0.1:8000/admin/`.

SQLite is used for local development. The generated `db.sqlite3` file is excluded from Git.

## Running the Developer Akademie frontend

The supplied frontend lives in a **separate repository** and is not included in this backend:

https://github.com/Developer-Akademie-Backendkurs/project.Quizly

Clone it into a separate directory alongside the backend:

```bash
git clone https://github.com/Developer-Akademie-Backendkurs/project.Quizly.git
```

Open the **frontend repository itself** as the VS Code workspace and serve its entry page using Live Server. Serving a parent directory instead can break root-relative paths such as `/pages/login.html` and `/assets/...`.

Run Django in a separate terminal. For local cookie-based authentication, use the same hostname for frontend and backend—for example, `http://127.0.0.1:5500` and `http://127.0.0.1:8000`. Mixing `localhost` and `127.0.0.1` can prevent cookies from being sent. Ensure the frontend API configuration points to the backend, the frontend includes credentials in API requests, and the backend's CORS configuration allows the chosen frontend origin.

## API endpoints

The following endpoints are based on the Developer Akademie endpoint documentation. Paths are relative to the backend origin.

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/api/register/` | Register a user |
| `POST` | `/api/login/` | Authenticate and set JWT cookies |
| `POST` | `/api/logout/` | Log out |
| `POST` | `/api/token/refresh/` | Refresh the access token |
| `GET` | `/api/quizzes/` | List the current user's quizzes |
| `POST` | `/api/quizzes/` | Create a quiz from a YouTube URL |
| `GET` | `/api/quizzes/{id}/` | Retrieve an owned quiz |
| `PATCH` | `/api/quizzes/{id}/` | Partially update an owned quiz |
| `DELETE` | `/api/quizzes/{id}/` | Delete an owned quiz |

Protected requests require valid JWT cookies. Clients must retain and send the cookies returned by the API. Requests for another user's quiz return `403 Forbidden`; a nonexistent quiz returns `404 Not Found`; unauthenticated requests return `401 Unauthorized`.

No additional mandatory API endpoints are introduced beyond the supplied specification.

## Quiz generation workflow

1. Accept a YouTube URL through `POST /api/quizzes/`.
2. Extract the audio using `yt-dlp` and FFmpeg.
3. Transcribe the audio locally using the cached Whisper `base` model.
4. Ask Gemini Flash to generate a quiz title, description, and ten questions with four answer options each.
5. Validate the generated structure and save the quiz and questions.

Generation requires access to YouTube and Gemini. Longer videos can take more time, and external service errors may prevent quiz creation.

## Tests and coverage

Run the Django test suite:

```bash
python manage.py test
```

Measure coverage:

```bash
coverage run manage.py test
coverage report -m
```

Optionally generate an HTML coverage report:

```bash
coverage html
```

Open `htmlcov/index.html` to inspect the report. The Developer Akademie Django/DRF checklist requires **at least 95% coverage in its PM tests at submission**. Passing local tests does not establish that threshold; verify coverage before submitting.

Check installed dependency consistency:

```bash
python -m pip check
```

## Project structure

```text
quizzly_backend/
├── auth_app/          # Authentication, JWT cookies, and API
│   └── api/
├── core/              # Django configuration and central routing
├── quiz_app/          # Quiz models, API, generation, and tests
│   └── api/
├── .env.example       # Example configuration; no real secrets
├── .gitignore
├── manage.py
├── requirements.txt
└── README.md
```

Local secrets, the SQLite database, virtual environments, coverage reports, and temporary audio files are excluded from version control.

## Developer Akademie submission notes

This educational backend follows the supplied Quizly and Django/DRF project checklists. Their requirements include documented API endpoints, a separate backend repository, an English README with complete setup instructions, a complete `requirements.txt`, JWT authentication via HTTP-only cookies, a usable Django admin interface, docstrings, PEP 8 conventions, and short, single-purpose functions. The checklists explicitly require documenting the **global FFmpeg installation**.

The supplied frontend handles the user-facing interface, including quiz playback and results; its source code is not part of this backend repository.

**Development only:** SQLite and Django's development server are intended for local use. Production deployment would require a dedicated deployment configuration, HTTPS, secure cookie settings, and an appropriate application server.
