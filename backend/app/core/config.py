from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

UPLOAD_FOLDER = BASE_DIR / "uploads"

UPLOAD_FOLDER.mkdir(exist_ok=True)
