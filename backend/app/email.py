"""Outgoing email: a console backend for dev/tests, and SMTP (e.g. Gmail) or Resend for real."""
import asyncio
import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage
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


class EmailLoginError(RuntimeError):
    pass


class SMTPSender:
    """Sends through an SMTP server with STARTTLS. With Gmail, use an app password, not the account password."""

    def __init__(self, host: str, port: int, username: str, password: str, from_addr: str) -> None:
        self.host, self.port = host, port
        self.username, self.password = username, password
        self.from_addr = from_addr

    def build(self, message: Message) -> EmailMessage:
        msg = EmailMessage()
        msg["From"] = self.from_addr
        msg["To"] = message.to
        msg["Subject"] = message.subject
        for name, value in message.headers.items():
            msg[name] = value
        msg.set_content(message.text)
        if message.html:
            msg.add_alternative(message.html, subtype="html")
        return msg

    def _send_sync(self, msg: EmailMessage) -> None:
        with smtplib.SMTP(self.host, self.port, timeout=20) as smtp:
            smtp.starttls()
            try:
                smtp.login(self.username, self.password)
            except (smtplib.SMTPAuthenticationError, smtplib.SMTPServerDisconnected) as e:
                # Gmail often just drops the connection on bad credentials.
                raise EmailLoginError(
                    f"{self.host} rejected the login for {self.username}. For Gmail, SMTP_PASSWORD must be "
                    "an app password (needs 2-Step Verification), not your account password."
                ) from e
            smtp.send_message(msg)

    async def send(self, message: Message) -> None:
        await asyncio.to_thread(self._send_sync, self.build(message))


def _make_sender() -> EmailSender:
    s = get_settings()
    if s.email_backend == "resend":
        return ResendSender(s.resend_api_key, s.email_from)
    if s.email_backend == "smtp":
        return SMTPSender(s.smtp_host, s.smtp_port, s.smtp_username, s.smtp_password, s.email_from)
    return ConsoleSender()


sender: EmailSender = _make_sender()


async def send(to: str, subject: str, text: str, **kw) -> None:
    await sender.send(Message(to=to, subject=subject, text=text, **kw))
