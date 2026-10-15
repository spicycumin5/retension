from app import email


class FakeSMTP:
    instances: list["FakeSMTP"] = []

    def __init__(self, host, port, timeout):
        self.host, self.port = host, port
        self.calls: list[str] = []
        self.sent = None
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.calls.append("quit")

    def starttls(self):
        self.calls.append("starttls")

    def login(self, user, password):
        self.calls.append(f"login {user} {password}")

    def send_message(self, msg):
        self.calls.append("send")
        self.sent = msg


async def test_smtp_sender_uses_starttls_login_and_builds_multipart(monkeypatch):
    monkeypatch.setattr(email.smtplib, "SMTP", FakeSMTP)
    FakeSMTP.instances.clear()
    sender = email.SMTPSender("smtp.gmail.com", 587, "me@gmail.com", "apppassword", "Retension <me@gmail.com>")
    await sender.send(
        email.Message(
            to="you@example.com",
            subject="2 problems to re-solve today",
            text="plain body",
            html="<p>html body</p>",
            headers={"List-Unsubscribe": "<https://x/unsub>"},
        )
    )
    [smtp] = FakeSMTP.instances
    assert (smtp.host, smtp.port) == ("smtp.gmail.com", 587)
    assert smtp.calls == ["starttls", "login me@gmail.com apppassword", "send", "quit"]
    msg = smtp.sent
    assert msg["From"] == "Retension <me@gmail.com>" and msg["To"] == "you@example.com"
    assert msg["List-Unsubscribe"] == "<https://x/unsub>"
    assert msg.get_body("plain").get_content().strip() == "plain body"
    assert msg.get_body("html").get_content().strip() == "<p>html body</p>"


async def test_brevo_payload_splits_sender_and_keeps_unsubscribe_headers():
    sender = email.BrevoSender("key", "Retension <me@gmail.com>")
    payload = sender.payload(
        email.Message(
            to="you@example.com",
            subject="s",
            text="plain",
            html="<p>html</p>",
            headers={"List-Unsubscribe": "<https://x/unsub>"},
        )
    )
    assert payload == {
        "sender": {"name": "Retension", "email": "me@gmail.com"},
        "to": [{"email": "you@example.com"}],
        "subject": "s",
        "textContent": "plain",
        "htmlContent": "<p>html</p>",
        "headers": {"List-Unsubscribe": "<https://x/unsub>"},
    }
    assert email.BrevoSender("key", "me@gmail.com").sender == {"email": "me@gmail.com"}


async def test_smtp_error_after_acceptance_is_not_a_failed_send(monkeypatch):
    import pytest

    class DroppedOnQuit(FakeSMTP):
        def __exit__(self, *exc):
            raise email.smtplib.SMTPServerDisconnected("Connection unexpectedly closed")

    class DroppedBeforeSend(FakeSMTP):
        def send_message(self, msg):
            raise email.smtplib.SMTPServerDisconnected("Connection unexpectedly closed")

    sender = email.SMTPSender("smtp.gmail.com", 587, "me@gmail.com", "apppassword", "me@gmail.com")
    message = email.Message(to="you@example.com", subject="s", text="t")
    monkeypatch.setattr(email.smtplib, "SMTP", DroppedOnQuit)
    await sender.send(message)
    monkeypatch.setattr(email.smtplib, "SMTP", DroppedBeforeSend)
    with pytest.raises(email.smtplib.SMTPServerDisconnected):
        await sender.send(message)


async def test_smtp_login_failure_explains_app_passwords(monkeypatch):
    import pytest

    class RejectingSMTP(FakeSMTP):
        def login(self, user, password):
            raise email.smtplib.SMTPServerDisconnected("Connection unexpectedly closed")

    monkeypatch.setattr(email.smtplib, "SMTP", RejectingSMTP)
    sender = email.SMTPSender("smtp.gmail.com", 587, "me@gmail.com", "wrong", "me@gmail.com")
    with pytest.raises(email.EmailLoginError, match="app password"):
        await sender.send(email.Message(to="you@example.com", subject="s", text="t"))
