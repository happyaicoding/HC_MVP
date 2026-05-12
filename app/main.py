"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Create all DB tables on startup (Alembic handles migrations in prod)."""
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="HC MVP",
        version="0.1.0",
        docs_url="/docs" if settings.app_env == "development" else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie="hc_session",
        https_only=(settings.app_env == "production"),
        same_site="lax",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://ai.rh888.tw"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.routers import auth, otp, users

    app.include_router(otp.router,   prefix="/api/otp")
    app.include_router(auth.router,  prefix="/api/auth")
    app.include_router(users.router, prefix="/api/users")

    # admin router registered in Phase 4:
    # from app.routers import admin
    # app.include_router(admin.router, prefix="/api/admin")

    app.mount("/static", StaticFiles(directory="static"), name="static")

    templates = Jinja2Templates(directory="templates")

    @app.get("/", tags=["pages"], include_in_schema=False)
    async def user_page(request: Request):
        """Serve the LIFF member registration page with LIFF_ID injected."""
        return templates.TemplateResponse(
            request, "user/index.html", {"liff_id": settings.liff_id}
        )

    @app.get("/health", tags=["infra"])
    async def health_check() -> dict[str, str]:
        """Liveness probe for deployment checks."""
        return {"status": "ok"}

    return app


app = create_app()
