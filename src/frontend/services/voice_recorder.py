VOICE_RECORDER_JS = """
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
            if (event.data && event.data.size > 0) chunks.push(event.data);
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

window.stopRecordingToBase64 = async () => {
    const recorder = window.voiceRecorder;
    if (!recorder.mediaRecorder) {
        return { ok: false, error: 'Chưa bắt đầu ghi âm.' };
    }
    const mediaRecorder = recorder.mediaRecorder;
    const stream = recorder.stream;
    const chunks = recorder.chunks || [];
    const mimeType = mediaRecorder.mimeType || 'audio/webm';
    return await new Promise((resolve) => {
        mediaRecorder.onstop = async () => {
            try {
                const blob = new Blob(chunks, { type: mimeType });
                const reader = new FileReader();
                reader.onloadend = () => {
                    const base64 = reader.result.split(',')[1];
                    resolve({ ok: true, base64, mimeType, filename: 'record.webm' });
                };
                reader.readAsDataURL(blob);
            } catch (error) {
                resolve({ ok: false, error: error?.message || String(error) });
            } finally {
                if (stream) stream.getTracks().forEach((t) => t.stop());
                recorder.mediaRecorder = null;
                recorder.stream = null;
                recorder.chunks = [];
            }
        };
        mediaRecorder.stop();
    });
};
"""
