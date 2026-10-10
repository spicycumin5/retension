"""Daily reminder email listing each user's due problems."""
import html
import logging
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import email, scheduling
from app.config import get_settings
from app.models import Card, User

log = logging.getLogger("recall.digest")


@dataclass
class RunResult:
    sent: int = 0
    skipped_nothing_due: int = 0
    failed: int = 0


def is_digest_time(user: User, at: datetime) -> bool:
    """True once the user's local clock reaches their digest hour, until a digest goes out that day.

    Using >= rather than == means a late or missed hourly run still sends that day.
    """
    local = at.astimezone(ZoneInfo(user.timezone))
    return local.hour >= user.digest_hour and user.last_digest_on != local.date()


def unsubscribe_url(user: User) -> str:
    return f"{get_settings().frontend_url}/unsubscribe?token={user.unsubscribe_token}"


def one_click_unsubscribe_url(user: User) -> str:
    return f"{get_settings().frontend_url}/api/email/unsubscribe?token={user.unsubscribe_token}"


def compose(user: User, queue: list[Card], overflow: int) -> email.Message:
    app_url = get_settings().frontend_url
    n = len(queue)
    subject = f"{n} {'problem' if n == 1 else 'problems'} to re-solve today"

    def label(card: Card) -> str:
        p = card.problem
        number = f"{p.lc_number}. " if p.lc_number else ""
        level = f" ({p.difficulty})" if p.difficulty else ""
        return f"{number}{p.title}{level}"

    lines = ["These are close to the point where you'd start forgetting them:", ""]
    lines += [f"- {label(c)}\n  {c.problem.url}" for c in queue]
    if overflow:
        lines += ["", f"{overflow} more overdue will show up once you clear these."]
    lines += [
        "",
        f"Rate each one after you solve it: {app_url}/",
        "",
        f"Stop these emails: {unsubscribe_url(user)}",
    ]

    items = "".join(
        f'<li style="margin:0 0 10px"><a href="{html.escape(c.problem.url)}" '
        f'style="color:#0f5257;font-weight:bold">{html.escape(label(c))}</a></li>'
        for c in queue
    )
    more = f"<p>{overflow} more overdue will show up once you clear these.</p>" if overflow else ""
    body_html = (
        '<div style="font-family:Arial,sans-serif;font-size:16px;line-height:1.5;color:#1c2433;max-width:560px">'
        f'<h1 style="font-size:24px;margin:0 0 8px">{html.escape(subject)}</h1>'
        "<p style=\"margin:0 0 16px;color:#5d6779\">These are close to the point where you'd start forgetting them.</p>"
        f'<ul style="padding-left:20px;margin:0 0 16px">{items}</ul>{more}'
        f'<p><a href="{app_url}/" style="display:inline-block;background:#0f5257;color:#fff;'
        'padding:10px 16px;border-radius:8px;text-decoration:none;font-weight:bold">Open today’s queue</a></p>'
        f'<p style="font-size:13px;color:#5d6779;margin-top:32px">You get this because daily reminders are on. '
        f'<a href="{html.escape(unsubscribe_url(user))}" style="color:#5d6779">Stop these emails</a></p>'
        "</div>"
    )
    return email.Message(
        to=user.email,
        subject=subject,
        text="\n".join(lines),
        html=body_html,
        headers={
            "List-Unsubscribe": f"<{one_click_unsubscribe_url(user)}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        },
    )


async def send_due_digests(session: AsyncSession, at: datetime) -> RunResult:
    result = RunResult()
    users = (
        await session.scalars(
            select(User).where(
                User.is_active.is_(True),
                User.is_verified.is_(True),
                User.digest_enabled.is_(True),
            )
        )
    ).all()

    for user in users:
        if not is_digest_time(user, at):
            continue
        local_today = scheduling.local_date(at, user.timezone)
        cards = (
            await session.scalars(
                select(Card).where(
                    Card.user_id == user.id,
                    Card.suspended.is_(False),
                    Card.due < scheduling.end_of_local_day(at, user.timezone),
                )
            )
        ).unique().all()
        if not cards:
            # Nothing due: mark the day as handled so we don't re-query every hour.
            user.last_digest_on = local_today
            await session.commit()
            result.skipped_nothing_due += 1
            continue

        queue, overflow = scheduling.build_queue(
            cards, Card.schedule_state, at, user.timezone, user.daily_review_cap
        )
        try:
            await email.sender.send(compose(user, queue, overflow))
        except Exception:
            log.exception("digest send failed for user %s", user.id)
            result.failed += 1
            continue
        user.last_digest_on = local_today
        await session.commit()
        result.sent += 1
    return result


async def unsubscribe(session: AsyncSession, token: str) -> bool:
    user = await session.scalar(select(User).where(User.unsubscribe_token == token))
    if user is None:
        return False
    user.digest_enabled = False
    await session.commit()
    return True

