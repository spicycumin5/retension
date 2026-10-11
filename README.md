# Recall

Spaced repetition for LeetCode. Log a problem after you solve it, rate how it went, and Recall
schedules when to re-solve it (FSRS), capped at a daily number of re-solves.

## Run locally

Backend (Python 3.12):

```sh
cd backend
python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt   # bin/ on macOS/Linux
cp .env.example .env              # use the SQLite DATABASE_URL if Docker isn't running
docker compose up -d              # from the repo root, for Postgres
.venv/Scripts/alembic upgrade head
.venv/Scripts/uvicorn app.main:app --reload --port 8000
```

Frontend:

```sh
cd frontend
npm install
npm run dev                       # http://localhost:5173, proxies /api to :8000
```

Daily reminder emails come from an hourly job. Run it by hand with
`.venv/Scripts/python -m app.jobs.send_digests` (from `backend/`). Each user gets one email
on days something is due, once their local time passes their chosen hour.

In dev, emails (verification, password reset) are printed to the backend console.
`POST /dev/time-travel {"days": 5}` shifts the server clock so reviews come due
(dev only; the browser's own clock isn't shifted, so relative dates in the UI will lag).

## Deploy (Render)

`render.yaml` is a Render Blueprint: one Docker web service (FastAPI serving the API under
`/api` plus the built frontend), an hourly cron job for the digest, and Postgres.

1. Create a [Resend](https://resend.com) account, verify a sending domain, and create an API key.
2. In Render: New, then Blueprint, then pick this repo.
3. When prompted, set `FRONTEND_URL` (the app's public URL), `EMAIL_FROM` (an address on your
   verified domain) and `RESEND_API_KEY`. `SECRET` is generated for you.

Migrations run automatically when the web service starts.

## Tests

```sh
cd backend && .venv/Scripts/python -m pytest
```

## Layout

- `backend/app/scheduling.py` – pure FSRS + load-balancing + queue logic
- `backend/app/api/` – problems (LeetCode lookup), cards, reviews, today's queue
- `backend/app/digest.py`, `backend/app/jobs/` – daily reminder email and its hourly job
- `backend/app/stats.py` – per-pattern recall, weakest first, and new-problem suggestions
- `backend/app/problem_bank.py` – well-known free problems per pattern, verified against LeetCode
- `backend/app/patterns.py` – pattern list and LeetCode-tag mapping
- `frontend/src/pages/` – Today, Log a problem, Library, Settings, auth screens
