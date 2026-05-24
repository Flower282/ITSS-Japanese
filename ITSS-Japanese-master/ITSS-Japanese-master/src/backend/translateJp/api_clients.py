import json
import os
from pathlib import Path

import requests

GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"


def speech_to_text(audio_file_path: str, language: str = "ja") -> str:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Thiếu GROQ_API_KEY trong biến môi trường")

    headers = {"Authorization": f"Bearer {api_key}"}

    with open(audio_file_path, "rb") as audio_file:
        files = {"file": audio_file}
        data = {
            "model": "whisper-large-v3",
            "language": language,
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


def _translate_with_google(text: str, source_lang: str, target_lang: str) -> str:
    response = requests.get(
        GOOGLE_TRANSLATE_URL,
        params={
            "client": "gtx",
            "sl": source_lang,
            "tl": target_lang,
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
                translated_text = _translate_with_google(text.strip(), "ja", "vi")
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


def translate_vietnamese_to_japanese(text: str, context: str = "") -> tuple[str, str | None]:
    if not text or not text.strip():
        raise RuntimeError("Không có văn bản để dịch")

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Thiếu GROQ_API_KEY trong biến môi trường")

    model = os.getenv("GROQ_TRANSLATION_MODEL", "llama-3.1-8b-instant").strip()
    system_prompt = (
        "Bạn là một dịch giả tiếng Việt sang tiếng Nhật. "
        "Hãy dịch tự nhiên, đúng nghĩa, giữ ngữ cảnh, chọn nghĩa phù hợp theo câu và bối cảnh. "
        "Chỉ trả về bản dịch tiếng Nhật, không giải thích thêm."
    )

    user_prompt = f"Câu tiếng Việt cần dịch:\n{text.strip()}"
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
                translated_text = _translate_with_google(text.strip(), "vi", "ja")
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


def _parse_json_response(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise RuntimeError("Groq trả về dữ liệu không phải JSON hợp lệ.")


def analyze_chat_history(text: str) -> dict:
    if not text or not text.strip():
        raise RuntimeError("Không có nội dung hội thoại để phân tích")

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Thiếu GROQ_API_KEY trong biến môi trường")

    model = os.getenv("GROQ_ANALYSIS_MODEL", "llama-3.1-8b-instant").strip()
    system_prompt = (
        """
Bạn là chuyên gia ngôn ngữ Nhật - Việt. Hãy phân tích đoạn chat và đưa ra gợi ý phản hồi.

QUY TẮC LOGIC:
1. Bạn chỉ được viết câu trả lời của Người Việt ở lượt tiếp theo, không được viết lại câu của Người Nhật.
2. KHÔNG được lặp lại nguyên văn hoặc gần nguyên văn bất kỳ câu nào đã xuất hiện trong hội thoại, đặc biệt là câu cuối cùng của Người Nhật.
3. KHÔNG hỏi lại những thông tin đối phương ĐÃ NÓI (ví dụ: họ đã hẹn giờ thì không hỏi lại mấy giờ, họ đã nói địa điểm thì không hỏi lại địa điểm).
4. Mỗi gợi ý phải là một phản hồi mới, có chức năng rõ ràng: xác nhận/đồng ý, hỏi chi tiết thật sự còn thiếu, hoặc từ chối/dời lịch một cách lịch sự.
5. Phải xác định rõ vị thế: Người Việt thường là cấp dưới hoặc người ít tuổi hơn trong các hội thoại này (dùng thể lịch sự/kính ngữ phù hợp).
6. Các gợi ý phải có tính thực tế cao trong đời sống tại Nhật và phải làm cuộc hội thoại tiến lên, không được đứng yên ở cùng một thông tin.

PHẢI TRẢ VỀ JSON THEO CẤU TRÚC:
{
    "analysis": "Phân tích xem thông tin nào đã chốt (giờ giấc, địa điểm), thông tin nào cần làm rõ.",
    "suggestions": [
        {
            "type": "Xác nhận & Đồng ý",
            "japanese": "câu tiếng Nhật",
            "vietnamese_meaning": "nghĩa",
            "nuance": "Giải thích tại sao dùng câu này"
        },
        {
            "type": "Hỏi thêm chi tiết",
            "japanese": "câu tiếng Nhật (ví dụ: hỏi cửa ra số mấy, vị trí cụ thể ở ga)",
            "vietnamese_meaning": "nghĩa",
            "nuance": "Sắc thái"
        },
        {
            "type": "Từ chối/Dời lịch",
            "japanese": "câu tiếng Nhật",
            "vietnamese_meaning": "nghĩa",
            "nuance": "Cách nói giảm nói tránh"
        }
    ]
}
"""
    )
    user_prompt = (
        "Hội thoại:\n"
        f"{text.strip()}\n\n"
        "Yêu cầu:\n"
        "- Tóm tắt ngữ cảnh bằng tiếng Việt (context_summary).\n"
        "- Gợi ý 3 câu trả lời tiếng Nhật, mỗi câu phải là một phản hồi mới của Người Việt cho câu cuối cùng của Người Nhật.\n"
        "- Không được sao chép lại câu cuối cùng trong hội thoại hoặc biến nó thành gợi ý.\n"
        "- Mỗi gợi ý phải khác nhau về ý định và không được trùng nghĩa nhau.\n"
        "- Mỗi gợi ý có romaji, ý nghĩa tiếng Việt, và phong cách (lịch sự/thân mật/trung lập).\n"
        "- Trả về JSON hợp lệ, không kèm giải thích."
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    response = requests.post(GROQ_CHAT_URL, headers=headers, json=payload, timeout=120)

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise RuntimeError(_groq_error_message(response)) from exc

    response_payload = response.json()
    choices = response_payload.get("choices", [])
    if not choices:
        raise RuntimeError(f"Groq không trả về kết quả phân tích hợp lệ: {response_payload}")

    message = choices[0].get("message", {})
    content = (message.get("content") or "").strip()
    if not content:
        raise RuntimeError(f"Groq không trả về nội dung phân tích: {response_payload}")

    analysis = _parse_json_response(content)
    if "context_summary" not in analysis:
        if "analysis" in analysis:
            analysis["context_summary"] = analysis["analysis"]
        else:
            raise RuntimeError(f"Groq trả về JSON sai cấu trúc: {analysis}")

    if "suggestions" not in analysis:
        raise RuntimeError(f"Groq trả về JSON sai cấu trúc: {analysis}")

    return analysis


def analyze_chat_history_file(file_path: str | Path) -> dict:
    history_path = Path(file_path)
    if not history_path.exists():
        raise RuntimeError(f"Không tìm thấy file hội thoại: {history_path}")

    text = history_path.read_text(encoding="utf-8")
    return analyze_chat_history(text)