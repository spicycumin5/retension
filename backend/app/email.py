"""Outgoing email: a console backend for dev/tests and Resend for production."""
from dataclasses import dataclass, field
from typing import Protocol

import httpx

from app.config import get_settings


@dataclass
class Message:
    to: str
    subject: str
    text: str
    html: str | None = None
    headers: dict[str, str] = field(default_factory=dict)


class EmailSender(Protocol):
    async def send(self, message: Message) -> None: ...


class ConsoleSender:
    def __init__(self) -> None:
        self.outbox: list[Message] = []

    async def send(self, message: Message) -> None:
        self.outbox.append(message)
        print(
            f"\n--- email to {message.to} ---\nSubject: {message.subject}\n\n{message.text}\n--- end email ---\n",
            flush=True,
        )


class ResendSender:
    URL = "https://api.resend.com/emails"

    def __init__(self, api_key: str, from_addr: str) -> None:
        self.api_key = api_key
        self.from_addr = from_addr

    async def send(self, message: Message) -> None:
        payload = {"from": self.from_addr, "to": [message.to], "subject": message.subject, "text": message.text}
        if message.html:
            payload["html"] = message.html
        if message.headers:
            payload["headers"] = message.headers
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(self.URL, json=payload, headers={"Authorization": f"Bearer {self.api_key}"})
            resp.raise_for_status()


def _make_sender() -> EmailSender:
    s = get_settings()
    if s.email_backend == "resend":
        return ResendSender(s.resend_api_key, s.email_from)
    return ConsoleSender()


sender: EmailSender = _make_sender()


async def send(to: str, subject: str, text: str, **kw) -> None:
    await sender.send(Message(to=to, subject=subject, text=text, **kw))
