# Retension

Spaced repetition for LeetCode. Log a problem after you solve it, rate how it went, and Retension
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

Daily reminder emails come from an hourly job (GitHub Actions in production). Run it by hand with
`.venv/Scripts/python -m app.jobs.send_digests` (from `backend/`). Each user gets one email
on days something is due, once their local time passes their chosen hour.

In dev, emails (verification, password reset) are printed to the backend console.
`POST /dev/time-travel {"days": 5}` shifts the server clock so reviews come due
(dev only; the browser's own clock isn't shifted, so relative dates in the UI will lag).

## Deploy for free

Four free services: **Vercel** runs the app (the built frontend, plus the API under `/api` as
Python functions; see `vercel.json`), **Neon** hosts Postgres, **GitHub Actions** runs the hourly
reminder job and applies migrations, and **Brevo** sends every email through its HTTPS API.

1. **Neon.** Create a free project and copy its connection string
   (`postgresql://...?sslmode=require`). It works as-is; the app converts it for its driver.
2. **Brevo.** Create a free account, add your email address under Senders (Brevo emails it a
   confirmation link), then create an API key under SMTP & API, then API keys.
3. **GitHub Actions.** In the repo's Settings, then Secrets and variables, then Actions, add
   `DATABASE_URL`, `FRONTEND_URL` (the app's URL, from step 4), `EMAIL_FROM` (e.g.
   `Retension <you@gmail.com>`, using the Brevo sender) and `BREVO_API_KEY`. Then open the
   Actions tab and run "Database migrations" once to create the tables. It runs again by itself
   whenever a push to main changes `backend/alembic/`.
4. **Vercel.** Add New, then Project, then import this repo; `vercel.json` sets up both parts.
   Under Environment Variables add `ENV=production`, `SECRET` (a random string of 32+
   characters, e.g. from `openssl rand -hex 32`), `COOKIE_SECURE=true`, `EMAIL_BACKEND=brevo`,
   `DATABASE_URL`, `FRONTEND_URL` (the `.vercel.app` URL; set it after the first deploy if you
   don't know it yet, then redeploy), `EMAIL_FROM` and `BREVO_API_KEY`.
5. **Check the reminders.** In the Actions tab, pick "Daily reminder emails" and use "Run
   workflow" once.

Brevo's free plan sends 300 emails a day, so this suits a personal tool or a small group. The
`Dockerfile` still builds the whole app as one container if you'd rather host it that way;
it runs migrations on start.

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
