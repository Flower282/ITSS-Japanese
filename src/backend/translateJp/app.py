import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

import sounddevice as sd
from dotenv import load_dotenv

from service import VoiceTranslationService


load_dotenv(override=True)


class VoiceTranslatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Voice Translator")
        self.root.geometry("980x680")
        self.root.minsize(860, 600)

        self.sample_rate = 16000
        self.channels = 1
        self.frames = []
        self.stream = None
        self.recording = False
        self.service = VoiceTranslationService(sample_rate=self.sample_rate)

        self.status_var = tk.StringVar(value="Sẵn sàng")
        self._build_ui()

    def _build_ui(self):
        try:
            style = ttk.Style()
            style.theme_use("clam")
        except Exception:
            pass

        main = ttk.Frame(self.root, padding=18)
        main.pack(fill="both", expand=True)

        header = ttk.Label(
            main,
            text="Ghi âm tiếng Nhật, xử lý nhiễu và dịch sang tiếng Việt",
            font=("Segoe UI", 18, "bold")
        )
        header.pack(anchor="w")

        sub = ttk.Label(
            main,
            text="Bấm ghi âm, nói tiếng Nhật vào micro, bấm dừng để xử lý và xem kết quả bên dưới."
        )
        sub.pack(anchor="w", pady=(6, 12))

        context_box = ttk.LabelFrame(main, text="Ngữ cảnh bổ sung cho việc dịch")
        context_box.pack(fill="x", pady=(0, 12))

        self.context_text = scrolledtext.ScrolledText(context_box, wrap="word", height=4)
        self.context_text.pack(fill="both", expand=True, padx=8, pady=8)

        context_hint = ttk.Label(
            context_box,
            text="Ví dụ: chủ đề hội thoại, lĩnh vực chuyên môn, tên người/tên riêng, hoặc nghĩa bạn muốn ưu tiên."
        )
        context_hint.pack(anchor="w", padx=8, pady=(0, 8))

        status_row = ttk.Frame(main)
        status_row.pack(fill="x", pady=(0, 12))

        ttk.Label(status_row, text="Trạng thái:").pack(side="left")
        ttk.Label(status_row, textvariable=self.status_var).pack(side="left", padx=(8, 0))

        button_row = ttk.Frame(main)
        button_row.pack(fill="x", pady=(0, 14))

        self.start_btn = ttk.Button(button_row, text="Bắt đầu ghi âm", command=self.start_recording)
        self.start_btn.pack(side="left")

        self.stop_btn = ttk.Button(button_row, text="Dừng và xử lý", command=self.stop_recording, state="disabled")
        self.stop_btn.pack(side="left", padx=10)

        result_area = ttk.Frame(main)
        result_area.pack(fill="both", expand=True)

        left_box = ttk.LabelFrame(result_area, text="Văn bản tiếng Nhật")
        left_box.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.original_text = scrolledtext.ScrolledText(left_box, wrap="word", height=20)
        self.original_text.pack(fill="both", expand=True, padx=8, pady=8)

        right_box = ttk.LabelFrame(result_area, text="Bản dịch tiếng Việt")
        right_box.pack(side="left", fill="both", expand=True, padx=(8, 0))

        self.translated_text = scrolledtext.ScrolledText(right_box, wrap="word", height=20)
        self.translated_text.pack(fill="both", expand=True, padx=8, pady=8)

    def _set_status(self, text):
        self.status_var.set(text)

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            self.root.after(0, lambda: self._set_status(f"Cảnh báo âm thanh: {status}"))
        self.frames.append(indata.copy())

    def start_recording(self):
        if self.recording:
            return

        self.frames = []

        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                callback=self._audio_callback
            )
            self.stream.start()
        except Exception as exc:
            messagebox.showerror("Lỗi ghi âm", str(exc))
            return

        self.recording = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self._set_status("Đang ghi âm...")

    def stop_recording(self):
        if not self.recording:
            return

        self.recording = False
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
        self._set_status("Đang dừng ghi âm và xử lý...")

        try:
            if self.stream is not None:
                self.stream.stop()
                self.stream.close()
                self.stream = None
        except Exception:
            pass

        threading.Thread(target=self._process_audio, daemon=True).start()

    def _process_audio(self):
        try:
            context = self.context_text.get("1.0", "end").strip()

            def status_callback(message: str) -> None:
                self.root.after(0, lambda msg=message: self._set_status(msg))

            status_callback("Đang lưu file âm thanh...")
            self.service.save_frames_to_wav(self.frames, self.service.raw_path)

            result = self.service.process_audio_file(
                self.service.raw_path,
                context=context,
                status_callback=status_callback,
            )

            self.root.after(
                0,
                lambda: self._show_result(
                    result.transcript,
                    result.translation,
                    result.warning,
                ),
            )
        except Exception as exc:
            self.root.after(0, lambda: messagebox.showerror("Lỗi xử lý", str(exc)))
            self.root.after(0, lambda: self._set_status("Đã xảy ra lỗi"))
        finally:
            self.root.after(0, lambda: self.start_btn.config(state="normal"))
            self.root.after(0, lambda: self.stop_btn.config(state="disabled"))

    def _show_result(self, transcript, translation, warning=None):
        self.original_text.delete("1.0", "end")
        self.original_text.insert("end", transcript or "")

        self.translated_text.delete("1.0", "end")
        self.translated_text.insert("end", translation or "")

        if warning:
            self._set_status(warning)
            messagebox.showwarning("Cảnh báo Groq", warning)
        else:
            self._set_status("Hoàn tất")


def main():
    root = tk.Tk()
    app = VoiceTranslatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()