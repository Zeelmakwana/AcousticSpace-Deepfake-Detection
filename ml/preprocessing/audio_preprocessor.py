import numpy as np
import librosa


def normalize_audio(audio):

    max_value = np.max(np.abs(audio))

    if max_value == 0:
        return audio

    normalized_audio = audio / max_value

    return normalized_audio


def trim_silence(audio):

    trimmed_audio, _ = librosa.effects.trim(
        audio,
        top_db=20
    )

    return trimmed_audio


def preprocess_audio(audio):

    audio = normalize_audio(audio)
    
    audio = trim_silence(audio)

    return audio