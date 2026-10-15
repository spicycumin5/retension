"""Fetch problem metadata from LeetCode's public (unofficial) endpoints."""
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

GRAPHQL_URL = "https://leetcode.com/graphql"
ALL_PROBLEMS_URL = "https://leetcode.com/api/problems/all/"
_HEADERS = {"User-Agent": "Mozilla/5.0 (Retension spaced-repetition app)", "Referer": "https://leetcode.com"}
_URL_RE = re.compile(r"leetcode\.(?:com|cn)/problems/([a-z0-9-]+)")

_QUESTION_QUERY = """
query q($slug: String!) {
  question(titleSlug: $slug) {
    questionFrontendId title titleSlug difficulty topicTags { slug }
  }
}
"""

_RECENT_QUERY = """
query r($username: String!, $limit: Int!) {
  matchedUser(username: $username) { username }
  recentAcSubmissionList(username: $username, limit: $limit) { title titleSlug timestamp }
}
"""
RECENT_LIMIT = 20  # LeetCode returns at most 20 regardless of the limit asked for

_number_to_slug: dict[int, str] = {}


class ResolveError(Exception):
    pass


@dataclass
class ProblemInfo:
    slug: str
    title: str
    lc_number: int | None = None
    difficulty: str | None = None
    lc_tags: list[str] = field(default_factory=list)


def parse_query(query: str) -> tuple[str, int | None]:
    """Returns ("slug", None) or ("", number). Raises ResolveError for junk input."""
    q = query.strip()
    if m := _URL_RE.search(q.lower()):
        return m.group(1), None
    if q.isdigit():
        return "", int(q)
    slug = re.sub(r"[^a-z0-9]+", "-", q.lower()).strip("-")
    if not slug:
        raise ResolveError("Enter a LeetCode URL, problem number or title")
    return slug, None


async def slug_for_number(number: int) -> str:
    if not _number_to_slug:
        async with httpx.AsyncClient(timeout=15, headers=_HEADERS) as client:
            resp = await client.get(ALL_PROBLEMS_URL)
            resp.raise_for_status()
        for item in resp.json()["stat_status_pairs"]:
            stat = item["stat"]
            _number_to_slug[int(stat["frontend_question_id"])] = stat["question__title_slug"]
    try:
        return _number_to_slug[number]
    except KeyError:
        raise ResolveError(f"No LeetCode problem #{number}") from None


async def fetch_problem(slug: str) -> ProblemInfo:
    async with httpx.AsyncClient(timeout=10, headers=_HEADERS) as client:
        resp = await client.post(
            GRAPHQL_URL, json={"query": _QUESTION_QUERY, "variables": {"slug": slug}}
        )
        resp.raise_for_status()
    q = (resp.json().get("data") or {}).get("question")
    if not q:
        raise ResolveError(f"No LeetCode problem '{slug}'")
    return ProblemInfo(
        slug=q["titleSlug"],
        title=q["title"],
        lc_number=int(q["questionFrontendId"]) if q["questionFrontendId"].isdigit() else None,
        difficulty=q["difficulty"],
        lc_tags=[t["slug"] for t in q["topicTags"]],
    )


@dataclass
class Solve:
    slug: str
    title: str
    solved_at: datetime


async def recent_accepted(username: str) -> list[Solve]:
    """Most recent accepted solve per problem, newest first."""
    async with httpx.AsyncClient(timeout=10, headers=_HEADERS) as client:
        resp = await client.post(
            GRAPHQL_URL,
            json={"query": _RECENT_QUERY, "variables": {"username": username, "limit": RECENT_LIMIT}},
        )
        resp.raise_for_status()
    data = resp.json().get("data") or {}
    if not data.get("matchedUser"):
        raise ResolveError(f"No LeetCode user named '{username}'")
    latest: dict[str, Solve] = {}
    for sub in data.get("recentAcSubmissionList") or []:
        solve = Solve(
            slug=sub["titleSlug"],
            title=sub["title"],
            solved_at=datetime.fromtimestamp(int(sub["timestamp"]), tz=timezone.utc),
        )
        if solve.slug not in latest or solve.solved_at > latest[solve.slug].solved_at:
            latest[solve.slug] = solve
    return sorted(latest.values(), key=lambda s: s.solved_at, reverse=True)
