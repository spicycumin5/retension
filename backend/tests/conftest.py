import os
import re
import tempfile

_db_file = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_db_file}"
os.environ["ENV"] = "dev"

import httpx  # noqa: E402
import pytest  # noqa: E402
from sqlalchemy import event  # noqa: E402

from app import clock, email, leetcode, ratelimit  # noqa: E402
from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@event.listens_for(engine.sync_engine, "connect")
def _sqlite_fks(dbapi_conn, _):
    dbapi_conn.execute("PRAGMA foreign_keys=ON")


FAKE_PROBLEMS = {
    "daily-temperatures": leetcode.ProblemInfo(
        slug="daily-temperatures", title="Daily Temperatures", lc_number=739,
        difficulty="Medium", lc_tags=["array", "stack", "monotonic-stack"],
    ),
    "two-sum": leetcode.ProblemInfo(
        slug="two-sum", title="Two Sum", lc_number=1, difficulty="Easy", lc_tags=["array", "hash-table"],
    ),
    "contains-duplicate": leetcode.ProblemInfo(
        slug="contains-duplicate", title="Contains Duplicate", lc_number=217, difficulty="Easy",
        lc_tags=["array", "hash-table", "sorting"],
    ),
    "number-of-islands": leetcode.ProblemInfo(
        slug="number-of-islands", title="Number of Islands", lc_number=200, difficulty="Medium",
        lc_tags=["array", "depth-first-search", "breadth-first-search", "union-find", "matrix"],
    ),
}


# The real implementation, for tests that exercise it against a mocked HTTP transport.
REAL_RECENT_ACCEPTED = leetcode.recent_accepted

# username -> recent solves, newest first; tests may replace entries
FAKE_RECENT: dict[str, list[leetcode.Solve]] = {}


@pytest.fixture(autouse=True)
async def _fresh_state(monkeypatch):
    async def fake_fetch(slug):
        if slug not in FAKE_PROBLEMS:
            raise leetcode.ResolveError(f"No LeetCode problem '{slug}'")
        return FAKE_PROBLEMS[slug]

    async def fake_slug_for_number(n):
        for p in FAKE_PROBLEMS.values():
            if p.lc_number == n:
                return p.slug
        raise leetcode.ResolveError(f"No LeetCode problem #{n}")

    async def fake_recent(username):
        if username not in FAKE_RECENT:
            raise leetcode.ResolveError(f"No LeetCode user named '{username}'")
        return FAKE_RECENT[username]

    FAKE_RECENT.clear()
    monkeypatch.setattr(leetcode, "recent_accepted", fake_recent)
    monkeypatch.setattr(leetcode, "fetch_problem", fake_fetch)
    monkeypatch.setattr(leetcode, "slug_for_number", fake_slug_for_number)
    monkeypatch.setattr(ratelimit, "enabled", False)
    email.sender.outbox.clear()
    clock.reset()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    clock.reset()


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test/api")


@pytest.fixture
async def client():
    async with _client() as c:
        yield c


async def signup(client: httpx.AsyncClient, email_addr: str = "a@example.com", tz: str = "UTC") -> None:
    """Register, verify via the emailed token, and log in (cookie stored on the client)."""
    r = await client.post("/auth/register", json={"email": email_addr, "password": "hunter2hunter2", "timezone": tz})
    assert r.status_code == 201, r.text
    message = email.sender.outbox[-1]
    assert message.to == email_addr
    token = re.search(r"token=(\S+)", message.text).group(1)
    r = await client.post("/auth/verify", json={"token": token})
    assert r.status_code == 200, r.text
    r = await client.post("/auth/login", data={"username": email_addr, "password": "hunter2hunter2"})
    assert r.status_code == 204, r.text


@pytest.fixture
async def user_client(client):
    await signup(client)
    return client


@pytest.fixture
def make_client():
    return _client
