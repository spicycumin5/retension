"""Check email settings by sending one message: python -m app.jobs.send_test_email you@example.com"""
import asyncio
import sys

from app import email
from app.config import get_settings


async def main(to: str) -> None:
    s = get_settings()
    await email.send(
        to,
        "Retension test email",
        f"Your Retension email settings work.\n\nBackend: {s.email_backend}\nFrom: {s.email_from}\n",
    )
    print(f"Sent a test email to {to} using the {s.email_backend} backend.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python -m app.jobs.send_test_email you@example.com")
    asyncio.run(main(sys.argv[1]))
