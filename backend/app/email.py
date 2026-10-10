"""Outgoing email. Console backend for now; a real provider plugs in behind EmailSender."""
import logging
from typing import Protocol

log = logging.getLogger("recall.email")


class EmailSender(Protocol):
    async def send(self, to: str, subject: str, text: str) -> None: ...


class ConsoleSender:
    def __init__(self) -> None:
        self.outbox: list[tuple[str, str, str]] = []

    async def send(self, to: str, subject: str, text: str) -> None:
        self.outbox.append((to, subject, text))
        print(f"\n--- email to {to} ---\nSubject: {subject}\n\n{text}\n--- end email ---\n", flush=True)


sender: EmailSender = ConsoleSender()
