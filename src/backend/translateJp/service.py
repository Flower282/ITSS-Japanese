from __future__ import annotations

from dataclasses import dataclass
import os
import tempfile
from typing import Callable

import numpy as np
from scipy.io import wavfile

try:
    from src.backend.translateJp.api_clients import (
        speech_to_text,
        translate_japanese_to_vietnamese,
        translate_vietnamese_to_japanese,
    )
    from src.backend.translateJp.audio_utils import reduce_noise_file
except ModuleNotFoundError:
    from api_clients import (
        speech_to_text,
        translate_japanese_to_vietnamese,
        translate_vietnamese_to_japanese,
    )
    from audio_utils import reduce_noise_file


@dataclass
class VoiceTranslationResult:
    transcript: str
    translation: str
    warning: str | None = None


class VoiceTranslationService:
    def __init__(
        self,
        sample_rate: int = 16000,
        raw_path: str | None = None,
        clean_path: str | None = None,
    ) -> None:
        self.sample_rate = sample_rate
        temp_dir = tempfile.gettempdir()
        self.raw_path = raw_path or os.path.join(temp_dir, "voice_raw.wav")
        self.clean_path = clean_path or os.path.join(temp_dir, "voice_clean.wav")

    def process_frames(
        self,
        frames: list[np.ndarray],
        context: str = "",
        direction: str = "ja-to-vi",
        status_callback: Callable[[str], None] | None = None,
    ) -> VoiceTranslationResult:
        if not frames:
            raise RuntimeError("Không có dữ liệu âm thanh để xử lý.")
        self.save_frames_to_wav(frames, self.raw_path)
        return self.process_audio_file(
            self.raw_path,
            context=context,
            direction=direction,
            status_callback=status_callback,
        )

    def save_frames_to_wav(self, frames: list[np.ndarray], output_path: str) -> None:
        audio = np.concatenate(frames, axis=0).squeeze()
        audio = np.clip(audio, -1.0, 1.0)
        wavfile.write(output_path, self.sample_rate, (audio * 32767).astype(np.int16))

    def process_audio_file(
        self,
        audio_path: str,
        context: str = "",
        direction: str = "ja-to-vi",
        status_callback: Callable[[str], None] | None = None,
    ) -> VoiceTranslationResult:
        warnings: list[str] = []

        if direction not in {"ja-to-vi", "vi-to-ja"}:
            raise RuntimeError("Hướng dịch không hợp lệ.")

        if status_callback:
            status_callback("Đang khử nhiễu...")
        stt_path = audio_path
        try:
            reduce_noise_file(audio_path, self.clean_path)
            stt_path = self.clean_path
        except Exception:
            warnings.append("Không thể khử nhiễu, sẽ dùng file gốc để nhận dạng.")

        if direction == "ja-to-vi":
            if status_callback:
                status_callback("Đang chuyển giọng nói Nhật thành văn bản...")
            transcript = speech_to_text(stt_path, language="ja")

            if status_callback:
                status_callback("Đang dịch sang tiếng Việt bằng Groq Llama...")
            translation, warning = translate_japanese_to_vietnamese(transcript, context=context)
        else:
            if status_callback:
                status_callback("Đang chuyển giọng nói Việt thành văn bản...")
            transcript = speech_to_text(stt_path, language="vi")

            if status_callback:
                status_callback("Đang dịch sang tiếng Nhật bằng Groq Llama...")
            translation, warning = translate_vietnamese_to_japanese(transcript, context=context)
        if warning:
            warnings.append(warning)

        combined_warning = " ".join(warnings) if warnings else None

        return VoiceTranslationResult(
            transcript=transcript,
            translation=translation,
            warning=combined_warning,
        )
