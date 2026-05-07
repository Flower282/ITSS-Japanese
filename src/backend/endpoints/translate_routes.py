from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, File, Form, UploadFile

from src.backend.translateJp.service import VoiceTranslationService

router = APIRouter()


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
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
