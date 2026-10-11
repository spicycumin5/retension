from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import digest
from app.api import cards, dev, imports, problems, stats
from app.config import get_settings
from app.db import get_session
from app.ratelimit import rate_limit
from app.users import UserCreate, UserRead, UserUpdate, auth_backend, fastapi_users

settings = get_settings()

# All API routes live on this app, mounted at /api below.
api = FastAPI(title="Recall API")

auth_limit = [Depends(rate_limit("auth", 10, 60))]
api.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth", tags=["auth"], dependencies=auth_limit)
api.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"], dependencies=auth_limit)
api.include_router(fastapi_users.get_verify_router(UserRead), prefix="/auth", tags=["auth"], dependencies=auth_limit)
api.include_router(fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"], dependencies=auth_limit)
api.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"])
api.include_router(problems.router)
api.include_router(cards.router)
api.include_router(stats.router)
api.include_router(imports.router)
if settings.is_dev:
    api.include_router(dev.router)


@api.get("/health")
async def health():
    return {"ok": True}


@api.post("/email/unsubscribe", status_code=204, dependencies=[Depends(rate_limit("unsubscribe", 20, 60))])
async def unsubscribe(token: str, session: AsyncSession = Depends(get_session)):
    """Turns off digest emails. POST only, so link scanners can't trigger it; also serves
    RFC 8058 one-click unsubscribe from mail clients."""
    if not await digest.unsubscribe(session, token):
        raise HTTPException(404, "This unsubscribe link is invalid.")


class SPAStaticFiles(StaticFiles):
    """Serves the built frontend, falling back to index.html for client-side routes."""

    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as e:
            if e.status_code != 404:
                raise
            return await super().get_response("index.html", scope)


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/api", api)
if settings.static_dir:
    app.mount("/", SPAStaticFiles(directory=settings.static_dir, html=True), name="frontend")
