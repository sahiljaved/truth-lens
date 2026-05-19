# TruthLens (News Validator)

Verify news claims from **text**, **images** (OCR), or **videos** (speech-to-text), then score them against live news sources.

| Layer | Stack |
|-------|--------|
| Frontend | React 18, Vite, MUI |
| Backend | Django 4.2, DRF, PostgreSQL |
| Extraction | Tesseract, Whisper, ffmpeg |
| Sources | GNews API, Google News RSS |

## Local development

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env        # edit secrets
python manage.py migrate
python manage.py runserver

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 — API proxied to http://127.0.0.1:8000.

## Deploy to production (shareable link)

See **[DEPLOY.md](./DEPLOY.md)** for step-by-step instructions to:

1. Push this repo to **GitHub**
2. Deploy with **Render** (free tier) using `render.yaml`
3. Get live URLs like `https://truthlens-frontend.onrender.com`

You will need a [GNews API key](https://gnews.io/) for news search in production.

## Project layout

```
backend/     Django API, Celery tasks, OCR/STT pipeline
frontend/    React UI
docs/        Interview guide (markdown + PDF)
render.yaml  One-click Render blueprint
```

## Security

- Never commit `backend/.env` (see `.gitignore`)
- API keys stay server-side only
- Use `config.settings.production` with `DEBUG=False` in production
