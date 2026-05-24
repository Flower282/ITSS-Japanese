import numpy as np
from scipy.io import wavfile

try:
    import noisereduce as nr
except ImportError:
    nr = None


def reduce_noise_file(input_path: str, output_path: str, noise_clip_seconds: float = 0.25) -> None:
    sample_rate, data = wavfile.read(input_path)

    if data.ndim > 1:
        data = data.mean(axis=1)

    data = data.astype(np.float32)

    max_abs = np.max(np.abs(data))
    if max_abs > 0:
        data = data / max_abs

    if nr is not None and len(data) > int(sample_rate * noise_clip_seconds):
        noise_sample = data[: int(sample_rate * noise_clip_seconds)]
        filtered = nr.reduce_noise(
            y=data,
            sr=sample_rate,
            y_noise=noise_sample,
            prop_decrease=0.9
        )
    else:
        filtered = data

    filtered = np.clip(filtered, -1.0, 1.0)
    wavfile.write(output_path, sample_rate, (filtered * 32767).astype(np.int16))