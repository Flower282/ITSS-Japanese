from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.backend.translateJp.api_clients import (
    translate_japanese_to_vietnamese,
    translate_vietnamese_to_japanese,
)
from src.backend.translateJp.service import VoiceTranslationService

router = APIRouter()


class TranslateTextRequest(BaseModel):
    text: str = Field(min_length=1)
    context: str = ""
    direction: str = Field(default="ja-to-vi", pattern="^(ja-to-vi|vi-to-ja)$")


@router.post("/audio")
@router.post("/translate-audio")
async def translate_audio(
    audio: UploadFile = File(...),
    context: str = Form(""),
) -> dict:
    service = VoiceTranslationService()
    suffix = os.path.splitext(audio.filename or "")[1] or ".wav"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(await audio.read())
        tmp_path = tmp_file.name

    try:
        result = service.process_audio_file(tmp_path, context=context)
        return {
            "transcript": result.transcript,
            "translation": result.translation,
            "warning": result.warning,
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


@router.post("")
@router.post("/translate-text")
async def translate_text(body: TranslateTextRequest) -> dict:
    """Translate text between Japanese and Vietnamese without audio."""
    try:
        if body.direction == "ja-to-vi":
            translation, warning = translate_japanese_to_vietnamese(
                body.text, context=body.context
            )
        else:
            translation, warning = translate_vietnamese_to_japanese(
                body.text, context=body.context
            )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "transcript": body.text,
        "translation": translation,
        "warning": warning,
    }
