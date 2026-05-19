from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env", override=True)

from nicegui import app, ui
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import RedirectResponse

from src.backend.endpoints import analysis, items, login, translate_routes, users, lang_routes
from fastapi import Request as FastAPIRequest
from src.core.config import settings
from src.core.i18n import (
    get_user_language,
    set_user_language,
    VALID_LANGUAGES,
    DEFAULT_LANGUAGE,
)
from src.db import init_db

# ruff: noqa: F401
from src.frontend.pages import (
    home,
    create_user,
    dashboard_page,
    items as items_page,
    login as login_page,
    translation_page,
    analysis_page,
    culture_page,
    translate_test_page,
)


async def on_startup():
    """Initializes the database on application startup."""
    print("INFO:     Initializing database...")
    init_db.init()
    print("INFO:     Database initialization complete.")


async def on_shutdown():
    """Actions to perform on application shutdown."""
    print("INFO:     Application shutting down.")


app.on_startup(on_startup)
app.on_shutdown(on_shutdown)
app.add_static_files("/images", str(ROOT_DIR / "images"))

# Add CORS middleware
#   - Only for external apps.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You should restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LanguagePrefixMiddleware(BaseHTTPMiddleware):
    # Paths that must NOT be redirected to a language-prefixed URL
    _EXCEPTION_PATHS = {'/login', '/home', '/favicon.ico'}
    _EXCEPTION_PREFIXES = (
        '/api/',
        '/images/',
        '/_nicegui/',
        '/_statics/',
        '/login/',
    )

    def __init__(self, app, prefixes=None):
        super().__init__(app)
        self.prefixes = prefixes or []

    def _is_exception(self, path: str) -> bool:
        """Return True for paths that should bypass lang-prefix redirect."""
        if path in self._EXCEPTION_PATHS:
            return True
        for prefix in self._EXCEPTION_PREFIXES:
            if path.startswith(prefix):
                return True
        return False

    def _has_lang_prefix(self, path: str) -> bool:
        """Return True if path already starts with a known /{lang}/ prefix."""
        for p in self.prefixes:
            if path == f'/{p}' or path.startswith(f'/{p}/'):
                return True
        return False

    async def dispatch(self, request, call_next):
        path = request.scope.get('path', '')

        # ------------------------------------------------------------------ #
        # 1. Redirect bare root → /{DEFAULT_LANGUAGE}
        # ------------------------------------------------------------------ #
        if path == '/':
            return RedirectResponse(url=f'/{DEFAULT_LANGUAGE}', status_code=302)

        # ------------------------------------------------------------------ #
        # 2. Redirect any app path that has NO lang prefix → /vn/{path}
        #    Skip exceptions (login, api, static assets, …)
        # ------------------------------------------------------------------ #
        if not self._has_lang_prefix(path) and not self._is_exception(path):
            return RedirectResponse(
                url=f'/{DEFAULT_LANGUAGE}{path}',
                status_code=302,
            )

        # ------------------------------------------------------------------ #
        # 3. Strip lang prefix so NiceGUI page handlers see the bare path,
        #    and inject detected lang into request.state BEFORE call_next so
        #    get_user_language() can read it within the same request.
        # ------------------------------------------------------------------ #
        detected_lang: str | None = None
        for p in self.prefixes:
            if path == f'/{p}' or path.startswith(f'/{p}/'):
                detected_lang = p
                new_path = path[len(p) + 1:] or '/'
                request.scope['path'] = new_path
                request.scope['raw_path'] = new_path.encode()
                break

        # Inject into request.state so page handlers can read it immediately
        if detected_lang:
            request.state.app_language = detected_lang

        response = await call_next(request)

        # Also persist in a long-lived cookie for subsequent navigations /
        # page reloads that arrive without a lang prefix in the URL.
        if detected_lang:
            response.set_cookie(
                key='app_language',
                value=detected_lang,
                max_age=60 * 60 * 24 * 365,  # 1 year
                httponly=False,
                samesite='lax',
            )

        return response


app.add_middleware(LanguagePrefixMiddleware, prefixes=VALID_LANGUAGES)

# API Routers
app.include_router(login.router, tags=["login"])
app.include_router(users.router, prefix="/api/v1", tags=["users"])
app.include_router(items.router, prefix="/api/v1", tags=["items"])
app.include_router(translate_routes.router, prefix="/api/v1/translate", tags=["translate"])
app.include_router(analysis.router, prefix="/api")
app.include_router(lang_routes.router)

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="NiceGUI FastAPI Template",
        port=8000,
        storage_secret=settings.SECRET_KEY,
        reload=True,
        fastapi_docs=True,
    )
