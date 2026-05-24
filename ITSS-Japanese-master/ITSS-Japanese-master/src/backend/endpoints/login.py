from typing import Any
from urllib.parse import urlencode
import secrets

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlmodel import Session
from nicegui import app

from src.core import security
from src.core.config import settings
from src.db.session import get_db
from src.repositories.user import user_repo

router = APIRouter()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_SCOPES = "openid email profile"


@router.post("/login/access-token")
def login_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """Authenticates a user via form data and returns a bearer access token upon success."""
    user = user_repo.authenticate(
        db=db, email=form_data.username, password=form_data.password
    )
    return {
        "access_token": security.create_access_token(user.id),
        "token_type": "bearer",
    }


@router.get("/login/google")
def login_google() -> RedirectResponse:
    """Redirects the user to Google's OAuth consent screen."""
    state_token = secrets.token_urlsafe(24)
    app.storage.general[f"oauth_state:{state_token}"] = True
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "state": state_token,
        "access_type": "online",
        "prompt": "select_account",
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/login/google/callback")
def login_google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Handles the OAuth callback, creates a JWT, and stores it in the UI session."""

    def redirect_with_error(message: str) -> RedirectResponse:
        error_id = secrets.token_urlsafe(12)
        app.storage.general[f"oauth_error:{error_id}"] = message
        return RedirectResponse(f"/login?error={error_id}")

    if error:
        return redirect_with_error("Google authentication was cancelled.")
    if not code:
        return redirect_with_error("Missing Google authorization code.")
    if not state or not app.storage.general.pop(f"oauth_state:{state}", None):
        return redirect_with_error("Invalid Google login state. Please try again.")

    try:
        token_response = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10.0,
        )
        token_response.raise_for_status()
    except httpx.HTTPError:
        return redirect_with_error("Google token exchange failed. Please retry.")

    token_data = token_response.json()
    google_token = token_data.get("id_token")
    if not google_token:
        return redirect_with_error("Missing Google ID token.")

    try:
        id_info = google_id_token.verify_oauth2_token(
            google_token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
    except ValueError:
        return redirect_with_error("Invalid Google ID token.")

    email = id_info.get("email")
    if not email:
        return redirect_with_error("Google account email not available.")

    full_name = id_info.get("name")
    picture = id_info.get("picture")
    user = user_repo.get_or_create_oauth_user(
        db=db, email=email, full_name=full_name
    )

    auth_data = {
        "access_token": security.create_access_token(user.id),
        "token_type": "bearer",
    }
    profile_name = full_name or email
    app.storage.general[f"oauth_result:{state}"] = {
        "auth": auth_data,
        "is_superuser": user.is_superuser,
        "profile": {
            "name": profile_name,
            "email": email,
            "picture": picture,
        },
    }
    return RedirectResponse(f"/login?state={state}")
