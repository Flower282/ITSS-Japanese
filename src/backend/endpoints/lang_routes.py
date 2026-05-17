"""
lang_routes.py — Language-prefixed URL support.

These routes are intentionally NO-OP pass-throughs. The actual routing is
handled by LanguagePrefixMiddleware in app.py, which strips the /{lang}/
prefix from the path before NiceGUI page handlers process the request.

We keep these FastAPI routes registered only to prevent 404 responses on
language-prefixed URLs before the middleware can act. They must NOT redirect
away from the requested URL.
"""

from fastapi import APIRouter, Request
from fastapi.responses import Response

router = APIRouter()


@router.get("/{lang}", include_in_schema=False)
async def lang_root(lang: str, request: Request) -> Response:
    """
    Placeholder for /{lang} — handled by LanguagePrefixMiddleware.
    This handler should never be reached for valid language prefixes
    because the middleware rewrites the path before routing.
    """
    # Return 200 with empty body; NiceGUI will handle actual page rendering
    # via its own internal routing after the middleware strips the lang prefix.
    return Response(status_code=200)


@router.get("/{lang}/{subpath:path}", include_in_schema=False)
async def lang_subpath(lang: str, subpath: str, request: Request) -> Response:
    """
    Placeholder for /{lang}/{subpath} — handled by LanguagePrefixMiddleware.
    """
    return Response(status_code=200)
