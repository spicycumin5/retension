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

Daily reminder emails come from an hourly job (GitHub Actions in production). Run it by hand with
`.venv/Scripts/python -m app.jobs.send_digests` (from `backend/`). Each user gets one email
on days something is due, once their local time passes their chosen hour.

In dev, emails (verification, password reset) are printed to the backend console.
`POST /dev/time-travel {"days": 5}` shifts the server clock so reviews come due
(dev only; the browser's own clock isn't shifted, so relative dates in the UI will lag).

## Deploy for free

Five free services: **Render** runs the app (one Docker web service serving the API under
`/api` plus the built frontend), **Neon** hosts Postgres, **GitHub Actions** runs the hourly
reminder job, and **Gmail** sends the reminders. Free Render services can't make outbound SMTP
connections, so the site's own emails (verification, password reset) go through **Brevo**'s
HTTPS API from the same Gmail address.

1. **Gmail app password.** Turn on 2-Step Verification for your Google account, then create an
   app password (Google Account, then Security, then App passwords). Use it instead of your
   normal password everywhere below. Test it locally first: in `backend/.env` set
   `EMAIL_BACKEND=smtp`, `EMAIL_FROM`, `SMTP_USERNAME` and `SMTP_PASSWORD`, then run
   `.venv/Scripts/python -m app.jobs.send_test_email you@gmail.com`.
2. **Neon.** Create a free project and copy its connection string
   (`postgresql://...?sslmode=require`). It works as-is; the app converts it for its driver.
3. **Brevo.** Create a free account, add your Gmail address under Senders (Brevo emails it a
   confirmation link), then create an API key under SMTP & API, then API keys.
4. **Render.** New, then Blueprint, then pick this repo. When prompted, set `DATABASE_URL`
   (from Neon), `FRONTEND_URL` (the app's onrender.com URL; set it after the first deploy if
   you don't know it yet), `EMAIL_FROM` (e.g. `Recall <you@gmail.com>`) and `BREVO_API_KEY`.
   Migrations run when the service starts.
5. **GitHub Actions.** In the repo's Settings, then Secrets and variables, then Actions, add
   `DATABASE_URL`, `FRONTEND_URL`, `EMAIL_FROM`, `SMTP_USERNAME` (your Gmail address) and
   `SMTP_PASSWORD` (the app password). GitHub's runners can use SMTP, so reminders go through
   Gmail directly. Then open the Actions tab, pick "Daily reminder emails" and use "Run workflow"
   once to check it.

Limits to know: the free Render service sleeps after 15 idle minutes and takes 30 to 60 seconds
to wake; Gmail allows roughly 500 emails a day and may send bulk mail from a personal address to
spam, so this suits a personal tool or a small group. For more users, switch to
`EMAIL_BACKEND=resend` with a verified domain.

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
