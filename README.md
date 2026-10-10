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

In dev, emails (verification, password reset) are printed to the backend console.
`POST /dev/time-travel {"days": 5}` shifts the server clock so reviews come due
(dev only; the browser's own clock isn't shifted, so relative dates in the UI will lag).

## Tests

```sh
cd backend && .venv/Scripts/python -m pytest
```

## Layout

- `backend/app/scheduling.py` – pure FSRS + load-balancing + queue logic
- `backend/app/api/` – problems (LeetCode lookup), cards, reviews, today's queue
- `backend/app/patterns.py` – pattern list and LeetCode-tag mapping
- `frontend/src/pages/` – Today, Log a problem, Library, Settings, auth screens
