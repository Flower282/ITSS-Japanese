from nicegui import ui


@ui.page("/translate-test")
async def translate_test_page() -> None:
    ui.label("Test ghi am va dich").classes("text-xl font-semibold")
    status_label = ui.label("San sang").classes("text-sm text-slate-500")

    columns = [
        {
            "name": "transcript",
            "label": "Van ban tieng Nhat",
            "field": "transcript",
            "align": "left",
        },
        {
            "name": "translation",
            "label": "Ban dich tieng Viet",
            "field": "translation",
            "align": "left",
        },
        {
            "name": "warning",
            "label": "Canh bao",
            "field": "warning",
            "align": "left",
        },
    ]
    table = ui.table(columns=columns, rows=[], row_key="transcript").classes(
        "w-full"
    )

    await ui.run_javascript(
        """
        window.voiceRecorder = window.voiceRecorder || {
            mediaRecorder: null,
            stream: null,
            chunks: [],
        };

        window.startRecording = async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                const chunks = [];
                const mediaRecorder = new MediaRecorder(stream);

                mediaRecorder.ondataavailable = (event) => {
                    if (event.data && event.data.size > 0) {
                        chunks.push(event.data);
                    }
                };

                mediaRecorder.start();

                window.voiceRecorder.mediaRecorder = mediaRecorder;
                window.voiceRecorder.stream = stream;
                window.voiceRecorder.chunks = chunks;

                return { ok: true };
            } catch (error) {
                return { ok: false, error: error?.message || String(error) };
            }
        };

        window.stopRecording = async () => {
            const recorder = window.voiceRecorder;
            if (!recorder.mediaRecorder) {
                return { ok: false, error: 'Chua bat dau ghi am.' };
            }

            const mediaRecorder = recorder.mediaRecorder;
            const stream = recorder.stream;
            const chunks = recorder.chunks || [];
            const mimeType = mediaRecorder.mimeType || 'audio/webm';

            return await new Promise((resolve) => {
                mediaRecorder.onstop = async () => {
                    try {
                        const blob = new Blob(chunks, { type: mimeType });
                        const formData = new FormData();
                        formData.append('audio', blob, 'record.webm');

                        const response = await fetch('/api/v1/translate/translate-audio', {
                            method: 'POST',
                            body: formData,
                        });

                        if (!response.ok) {
                            const text = await response.text();
                            resolve({ ok: false, error: text || 'Server error' });
                            return;
                        }

                        const data = await response.json();
                        resolve({ ok: true, data });
                    } catch (error) {
                        resolve({ ok: false, error: error?.message || String(error) });
                    } finally {
                        if (stream) {
                            stream.getTracks().forEach((track) => track.stop());
                        }
                        recorder.mediaRecorder = null;
                        recorder.stream = null;
                        recorder.chunks = [];
                    }
                };

                mediaRecorder.stop();
            });
        };
        """
    )

    async def on_start_recording() -> None:
        status_label.text = "Dang ghi am..."
        result = await ui.run_javascript("return await startRecording()")
        if not result or not result.get("ok"):
            status_label.text = "Khong the ghi am"
            ui.notify(result.get("error") if result else "Khong the ghi am", type="negative")

    async def on_stop_recording() -> None:
        status_label.text = "Dang xu ly..."
        result = await ui.run_javascript("return await stopRecording()", timeout=120.0)
        if not result or not result.get("ok"):
            status_label.text = "Loi xu ly"
            ui.notify(result.get("error") if result else "Loi xu ly", type="negative")
            return

        data = result.get("data", {})
        table.rows = [
            {
                "transcript": data.get("transcript", ""),
                "translation": data.get("translation", ""),
                "warning": data.get("warning") or "",
            }
        ]
        table.update()
        status_label.text = "Hoan tat"

    with ui.row().classes("gap-2"):
        ui.button("Ghi am", on_click=on_start_recording)
        ui.button("Dung ghi am", on_click=on_stop_recording)
