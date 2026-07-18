import shutil
from pathlib import Path
from fastapi import HTTPException
import uuid

from app.core.config import (
    UPLOAD_FOLDER,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE
)

def validate_audio(file):
    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only audio files are allowed."
        )

def save_uploaded_file(file):
    validate_audio(file)

    # Read the uploaded file
    contents = file.file.read()

    # Check file size
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File size exceeds 20 MB."
        )

    # Reset file pointer
    file.file.seek(0)

    # Save the file
    unique_filename = f"{uuid.uuid4()}-{file.filename}"
    file_path = UPLOAD_FOLDER / unique_filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return file_path
    
