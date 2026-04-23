from fastapi import Request
from nicegui import app, ui
from src.frontend import state
from src.frontend.components import notifications

GOOGLE_G_SVG = """
<svg width="20" height="20" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path fill="#EA4335" d="M24 9.5c3.5 0 6.4 1.2 8.7 3.4l6.5-6.5C35.5 2.5 30.2 0 24 0 14.6 0 6.4 5.4 2.3 13.3l7.6 5.9C11.8 13.3 17.4 9.5 24 9.5z"/>
  <path fill="#4285F4" d="M46.5 24.5c0-1.7-.2-3.4-.5-5H24v9.5h12.7c-.6 3-2.4 5.5-5 7.2l7.6 5.9c4.4-4.1 7.2-10.2 7.2-17.6z"/>
  <path fill="#FBBC05" d="M9.9 28.2c-1-3-1-6.4 0-9.4l-7.6-5.9c-3.3 6.6-3.3 14.6 0 21.2l7.6-5.9z"/>
  <path fill="#34A853" d="M24 48c6.2 0 11.5-2 15.3-5.4l-7.6-5.9c-2.1 1.4-4.9 2.2-7.7 2.2-6.6 0-12.2-3.8-14.1-9.3l-7.6 5.9C6.4 42.6 14.6 48 24 48z"/>
</svg>
"""


@ui.page("/login")
def login_page(request: Request):
    """Defines the Google-based login page."""
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
            "w-full max-w-md items-center rounded-2xl bg-white p-8 shadow-md"
        ):
            with ui.column().classes("items-center w-full text-center gap-2"):
                ui.image("images/logoitsss.png").classes(
                    "h-16 w-16 rounded-2xl shadow-sm mx-auto"
                ).on("click", lambda: ui.navigate.to("/"))
                ui.label("TrueTalk").classes("text-blue-700 text-2xl font-bold")
                ui.label("Trợ lý giao tiếp đa văn hóa Việt - Nhật").classes(
                    "text-sm text-slate-500"
                )

            ui.separator().classes("my-6 w-full")

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
