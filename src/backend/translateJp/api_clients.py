import os
import requests

GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"


def speech_to_text(audio_file_path: str) -> str:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Thiếu GROQ_API_KEY trong biến môi trường")

    headers = {"Authorization": f"Bearer {api_key}"}

    with open(audio_file_path, "rb") as audio_file:
        files = {"file": audio_file}
        data = {
            "model": "whisper-large-v3",
            "language": "ja"
        }
        response = requests.post(
            GROQ_URL,
            headers=headers,
            files=files,
            data=data,
            timeout=120
        )

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        if response.status_code in (401, 403):
            raise RuntimeError(
                "Groq từ chối xác thực (401/403). Hãy kiểm tra lại GROQ_API_KEY trong .env, "
                "hoặc tạo key Groq mới nếu key hiện tại đã hết hạn/bị thu hồi."
            ) from exc
        raise
    payload = response.json()

    if "text" not in payload:
        raise RuntimeError(f"Groq trả về dữ liệu không hợp lệ: {payload}")

    return payload["text"].strip()


def _translate_with_google(text: str) -> str:
    response = requests.get(
        GOOGLE_TRANSLATE_URL,
        params={
            "client": "gtx",
            "sl": "ja",
            "tl": "vi",
            "dt": "t",
            "ie": "UTF-8",
            "oe": "UTF-8",
            "q": text,
        },
        timeout=60,
    )
    response.raise_for_status()

    payload = response.json()
    translated_parts = []

    for item in payload[0]:
        if item and item[0]:
            translated_parts.append(item[0])

    translated_text = "".join(translated_parts).strip()
    if not translated_text:
        raise RuntimeError(f"Google Translate không trả về kết quả hợp lệ: {payload}")

    return translated_text


def _groq_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except Exception:
        payload = {}

    error = payload.get("error", {}) if isinstance(payload, dict) else {}
    message = (error.get("message") or response.text or "").strip()
    code = (error.get("code") or "").strip().lower() if isinstance(error, dict) else ""

    if response.status_code == 429 or "quota" in message.lower() or code in {"insufficient_quota", "rate_limit_exceeded"}:
        return "Groq đang hết quota hoặc bị giới hạn tốc độ."

    if response.status_code in (401, 403):
        return "Groq từ chối xác thực hoặc không cho phép model này."

    if response.status_code == 400 and ("model" in message.lower() or "not found" in message.lower() or "unavailable" in message.lower()):
        return "Model Groq hiện không khả dụng hoặc không còn miễn phí."

    if message:
        return f"Groq trả về lỗi: {message}"

    return f"Groq trả về lỗi HTTP {response.status_code}."


def translate_japanese_to_vietnamese(text: str, context: str = "") -> tuple[str, str | None]:
    if not text or not text.strip():
        raise RuntimeError("Không có văn bản để dịch")

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Thiếu GROQ_API_KEY trong biến môi trường")

    model = os.getenv("GROQ_TRANSLATION_MODEL", "llama-3.1-8b-instant").strip()
    system_prompt = (
        "Bạn là một dịch giả tiếng Nhật sang tiếng Việt. "
        "Hãy dịch tự nhiên, đúng nghĩa, giữ ngữ cảnh, chọn nghĩa phù hợp theo câu và bối cảnh. "
        "Chỉ trả về bản dịch tiếng Việt, không giải thích thêm."
    )

    user_prompt = f"Câu tiếng Nhật cần dịch:\n{text.strip()}"
    if context and context.strip():
        user_prompt += f"\n\nNgữ cảnh bổ sung từ người dùng:\n{context.strip()}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    response = requests.post(GROQ_CHAT_URL, headers=headers, json=payload, timeout=120)

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        fallback_reason = _groq_error_message(response)
        if response.status_code in (401, 403, 429) or response.status_code == 400:
            try:
                translated_text = _translate_with_google(text.strip())
            except Exception as google_exc:
                raise RuntimeError(
                    f"{fallback_reason} Không thể fallback sang Google Translate: {google_exc}"
                ) from exc

            warning = f"{fallback_reason} Đã fallback sang Google Translate."
            return translated_text, warning

        raise RuntimeError(fallback_reason) from exc

    response_payload = response.json()
    choices = response_payload.get("choices", [])
    if not choices:
        raise RuntimeError(f"Groq không trả về kết quả dịch hợp lệ: {response_payload}")

    message = choices[0].get("message", {})
    translated_text = (message.get("content") or "").strip()
    if not translated_text:
        raise RuntimeError(f"Groq không trả về nội dung dịch: {response_payload}")

    return translated_text, None