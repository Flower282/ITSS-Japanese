from fastapi import HTTPException, Request
from nicegui import app, ui
from src.core import security
from src.db.session import get_db_context
from src.frontend import state
from src.frontend.components import notifications
from src.repositories.user import user_repo

GOOGLE_G_SVG = """
<svg width="20" height="20" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path fill="#EA4335" d="M24 9.5c3.5 0 6.4 1.2 8.7 3.4l6.5-6.5C35.5 2.5 30.2 0 24 0 14.6 0 6.4 5.4 2.3 13.3l7.6 5.9C11.8 13.3 17.4 9.5 24 9.5z"/>
  <path fill="#4285F4" d="M46.5 24.5c0-1.7-.2-3.4-.5-5H24v9.5h12.7c-.6 3-2.4 5.5-5 7.2l7.6 5.9c4.4-4.1 7.2-10.2 7.2-17.6z"/>
  <path fill="#FBBC05" d="M9.9 28.2c-1-3-1-6.4 0-9.4l-7.6-5.9c-3.3 6.6-3.3 14.6 0 21.2l7.6-5.9z"/>
  <path fill="#34A853" d="M24 48c6.2 0 11.5-2 15.3-5.4l-7.6-5.9c-2.1 1.4-4.9 2.2-7.7 2.2-6.6 0-12.2-3.8-14.1-9.3l-7.6 5.9C6.4 42.6 14.6 48 24 48z"/>
</svg>
"""


def _complete_login(user) -> None:
    state.set_auth(
        {
            "access_token": security.create_access_token(user.id),
            "token_type": "bearer",
        }
    )
    app.storage.user["is_superuser"] = user.is_superuser
    state.set_profile(
        {
            "name": user.full_name or user.email,
            "email": user.email,
        }
    )
    ui.navigate.to("/")


async def login_with_password(email_input: ui.input, password_input: ui.input) -> None:
    try:
        with get_db_context() as db:
            user = user_repo.authenticate(
                db=db,
                email=email_input.value.strip(),
                password=password_input.value,
            )
        _complete_login(user)
    except HTTPException as e:
        notifications.show_error(e.detail)
    except Exception:
        notifications.show_error("Đăng nhập thất bại. Vui lòng thử lại.")


@ui.page("/login")
def login_page(request: Request):
    """Login page: Google OAuth or email/password (superuser and local accounts)."""
    if state.get_auth():
        ui.navigate.to("/")
        return

    error_message = None
    state_param = request.query_params.get("state")
    if state_param:
        pending_auth = app.storage.general.pop(f"oauth_result:{state_param}", None)
        if pending_auth:
            state.set_auth(pending_auth["auth"])
            app.storage.user["is_superuser"] = pending_auth.get(
                "is_superuser", False
            )
            state.set_profile(pending_auth.get("profile"))
            ui.navigate.to("/")
            return
        error_message = "Login session expired. Please try again."

    error_param = request.query_params.get("error")
    if error_param:
        error_message = app.storage.general.pop(
            f"oauth_error:{error_param}", error_message
        )

    with ui.column().classes(
        "min-h-screen w-full items-center justify-center bg-slate-50 p-6"
    ):
        with ui.card().classes(
            "w-full max-w-md rounded-2xl bg-white p-8 shadow-md"
        ):
            with ui.column().classes("items-center w-full text-center gap-2"):
                ui.image("/images/logoitsss.png").classes(
                    "h-16 w-16 rounded-2xl shadow-sm mx-auto"
                ).on("click", lambda: ui.navigate.to("/"))
                ui.label("TrueTalk").classes("text-blue-700 text-2xl font-bold")
                ui.label("Trợ lý giao tiếp đa văn hóa Việt - Nhật").classes(
                    "text-sm text-slate-500"
                )

            ui.separator().classes("my-6 w-full")

            with ui.column().classes("w-full gap-3"):
                email = (
                    ui.input("Email")
                    .props("autocomplete=username outlined dense")
                    .classes("w-full")
                )
                password = (
                    ui.input("Mật khẩu")
                    .props("type=password autocomplete=current-password outlined dense")
                    .classes("w-full")
                )
                ui.button(
                    "Đăng nhập",
                    on_click=lambda: login_with_password(email, password),
                ).props("color=primary unelevated").classes("w-full mt-1")
                email.on(
                    "keydown.enter", lambda: login_with_password(email, password)
                )
                password.on(
                    "keydown.enter", lambda: login_with_password(email, password)
                )

            with ui.row().classes("w-full items-center gap-3 my-4"):
                ui.separator().classes("flex-grow")
                ui.label("hoặc").classes("text-slate-400 text-sm")
                ui.separator().classes("flex-grow")

            google_button = ui.element("button").classes(
                "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 transition hover:bg-slate-50"
            )
            google_button.on("click", lambda: ui.navigate.to("/login/google"))
            with google_button:
                with ui.row().classes("items-center justify-center gap-3"):
                    ui.html(GOOGLE_G_SVG, sanitize=False)
                    ui.label("Đăng nhập bằng Google").classes(
                        "text-slate-700 font-medium"
                    )

            ui.label(
                "Bằng việc đăng nhập, bạn đồng ý với Điều khoản dịch vụ và Chính sách bảo mật của chúng tôi."
            ).classes("text-xs text-slate-400 text-center mt-4 leading-5")

    if error_message:
        notifications.show_error(error_message)
