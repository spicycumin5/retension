from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import cards, dev, problems
from app.config import get_settings
from app.ratelimit import rate_limit
from app.users import UserCreate, UserRead, UserUpdate, auth_backend, fastapi_users

settings = get_settings()

app = FastAPI(title="Recall API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

auth_limit = [Depends(rate_limit("auth", 10, 60))]
app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth", tags=["auth"], dependencies=auth_limit)
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"], dependencies=auth_limit)
app.include_router(fastapi_users.get_verify_router(UserRead), prefix="/auth", tags=["auth"], dependencies=auth_limit)
app.include_router(fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"], dependencies=auth_limit)
app.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"])
app.include_router(problems.router)
app.include_router(cards.router)
if settings.is_dev:
    app.include_router(dev.router)


@app.get("/health")
async def health():
    return {"ok": True}
