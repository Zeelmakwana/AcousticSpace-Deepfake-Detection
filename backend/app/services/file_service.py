import shutil
from pathlib import Path
from fastapi import HTTPException

from app.core.config import UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}

def validate_audio(file):
    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only audio files are allowed."
        )

def save_uploaded_file(file):
    validate_audio(file)
    file_path = UPLOAD_FOLDER / file.filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return file_path
    
