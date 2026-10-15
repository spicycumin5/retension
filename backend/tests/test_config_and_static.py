import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from app.config import Settings
from app.main import SPAStaticFiles


def test_database_url_gets_async_driver():
    s = Settings(database_url="postgres://u:p@host:5432/db")
    assert s.database_url == "postgresql+asyncpg://u:p@host:5432/db"


def test_production_requires_real_secret():
    with pytest.raises(ValidationError, match="SECRET"):
        Settings(env="production")
    Settings(env="production", secret="x" * 40)


def test_production_resend_requires_key():
    with pytest.raises(ValidationError, match="RESEND_API_KEY"):
        Settings(env="production", secret="x" * 40, email_backend="resend")


def test_production_brevo_requires_key():
    with pytest.raises(ValidationError, match="BREVO_API_KEY"):
        Settings(env="production", secret="x" * 40, email_backend="brevo")


async def test_spa_fallback_serves_index_for_client_routes(tmp_path):
    (tmp_path / "index.html").write_text("<html>app</html>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log(1)")
    app = FastAPI()
    app.mount("/", SPAStaticFiles(directory=tmp_path, html=True))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        assert (await c.get("/assets/app.js")).text == "console.log(1)"
        r = await c.get("/library")
        assert r.status_code == 200 and "app" in r.text


def test_neon_url_options_are_translated_for_asyncpg():
    s = Settings(database_url="postgresql://u:p@ep-x.neon.tech/neondb?sslmode=require&channel_binding=require")
    assert s.database_url == "postgresql+asyncpg://u:p@ep-x.neon.tech/neondb?ssl=require"


def test_plain_urls_are_untouched():
    url = "postgresql+asyncpg://recall:recall@localhost:5432/recall"
    assert Settings(database_url=url).database_url == url
    assert Settings(database_url="sqlite+aiosqlite:///x.db").database_url == "sqlite+aiosqlite:///x.db"


def test_production_smtp_requires_credentials_and_strips_app_password_spaces():
    with pytest.raises(ValidationError, match="SMTP_USERNAME"):
        Settings(env="production", secret="x" * 40, email_backend="smtp")
    s = Settings(env="production", secret="x" * 40, email_backend="smtp",
                 smtp_username="me@gmail.com", smtp_password="abcd efgh ijkl mnop")
    assert s.smtp_password == "abcdefghijklmnop"
