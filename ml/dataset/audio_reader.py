"""
audio_reader.py

Purpose:
Read an audio file and return
audio waveform with sample rate.
"""

from pathlib import Path
import librosa


def load_audio(audio_path):

    audio_path = Path(audio_path)

    audio, sample_rate = librosa.load(
        audio_path,
        sr=None
    )

    return audio, sample_rate

if __name__ == "__main__":

    path = r"E:\datasets\ASVspoof2019_LA_train\flac\LA_T_1000137.flac"

    audio, sample_rate = load_audio(path)

    print(sample_rate)

    print(type(audio))
    print(audio.shape)
    print(audio.dtype)
    print(audio[:10])