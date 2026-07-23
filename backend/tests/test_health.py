"""Basic smoke tests for the AcousticSpace API."""

import io
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "AcousticSpace API"


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "timestamp" in body


def test_model_info():
    response = client.get("/model-info")
    assert response.status_code == 200
    body = response.json()
    assert "mode" in body
    assert "checkpoint_path" in body
    assert "checkpoint_found" in body
    assert "device" in body
    assert "architecture" in body


def test_history_empty_or_list():
    response = client.get("/history")
    assert response.status_code == 200
    body = response.json()
    assert "results" in body
    assert isinstance(body["results"], list)


def test_analyze_invalid_format():
    """Uploading a non-audio file should return HTTP 400."""
    fake_txt = io.BytesIO(b"this is not audio")
    response = client.post(
        "/analyze",
        files={"file": ("test.txt", fake_txt, "text/plain")},
    )
    assert response.status_code == 400


def test_analyze_valid_wav():
    """Uploading a minimal valid WAV file should return HTTP 200 with AnalyzeResponse shape."""
    import struct
    import wave

    # Build a minimal in-memory WAV (1 channel, 16-bit, 22050 Hz, 0.1 s)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(22050)
        num_frames = 2205  # 0.1 seconds
        wf.writeframes(b"\x00\x00" * num_frames)
    buf.seek(0)

    response = client.post(
        "/analyze",
        files={"file": ("test.wav", buf, "audio/wav")},
    )
    assert response.status_code == 200
    body = response.json()
    # Assert complete AnalyzeResponse shape
    assert "id" in body
    assert "filename" in body
    assert "prediction" in body
    assert "confidence" in body
    assert "suspicious_segments" in body
    assert "room_acoustics_match" in body
    assert "breathing_consistency" in body
    assert "inference_time_sec" in body
    assert "timestamp" in body
