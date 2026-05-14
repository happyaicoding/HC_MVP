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
    """Create all DB tables on startup.

    Development / CI: create_all acts as a convenience fallback so the app
    starts without running Alembic manually.
    Production: Alembic (deploy.sh → alembic upgrade head) is the authority;
    create_all is a no-op when every table already exists.
    Tests: DB is managed entirely by the reset_db fixture (conftest.py);
    create_all here runs on the app engine, not the test engine, so it is
    harmless but redundant — tests never use this engine.
    """
    from app.config import get_settings
    settings = get_settings()
    if settings.app_env != "test":
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
        # https_only=False: Nginx terminates TLS and enforces HTTP→HTTPS
        # redirect, so the Secure flag is not needed at the app layer.
        # Setting https_only=True would break TestClient (HTTP transport)
        # because Python's cookiejar drops Secure cookies on non-HTTPS
        # requests, causing session loss after login.
        https_only=False,
        same_site="lax",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://ai.rh888.tw"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.routers import admin, auth, otp, users

    app.include_router(otp.router,   prefix="/api/otp")
    app.include_router(auth.router,  prefix="/api/auth")
    app.include_router(users.router, prefix="/api/users")
    app.include_router(admin.router, prefix="/api/admin")

    app.mount("/static", StaticFiles(directory="static"), name="static")

    templates = Jinja2Templates(directory="templates")

    @app.get("/", tags=["pages"], include_in_schema=False)
    async def user_page(request: Request):
        """Serve the LIFF member registration page with LIFF_ID injected."""
        return templates.TemplateResponse(
            request, "user/index.html", {"liff_id": settings.liff_id}
        )

    @app.get("/admin", tags=["pages"], include_in_schema=False)
    async def admin_page(request: Request):
        """Serve the admin login / dashboard page."""
        return templates.TemplateResponse(request, "admin/index.html", {})

    @app.get("/health", tags=["infra"])
    async def health_check() -> dict[str, str]:
        """Liveness probe for deployment checks."""
        return {"status": "ok"}

    return app


app = create_app()
