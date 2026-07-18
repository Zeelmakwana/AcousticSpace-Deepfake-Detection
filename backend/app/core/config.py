from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Upload folder
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

# Allowed audio formats
ALLOWED_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".flac",
    ".ogg",
    ".m4a"
}

# Maximum upload size (20 MB)
MAX_FILE_SIZE = 20 * 1024 * 1024

# API information
API_TITLE = "AcousticSpace Deepfake Detection API"
API_VERSION = "1.0.0"
API_DESCRIPTION = "Backend API for Deepfake Audio Detection"
