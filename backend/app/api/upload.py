from fastapi import APIRouter, UploadFile, File
from app.schemas.response import UploadResponse
from app.services.file_service import save_uploaded_file
from app.utils.logger import logger

router = APIRouter(tags=["Upload"])

@router.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    logger.info(f"Uploaded file: {file.filename}")

    path = save_uploaded_file(file)

    return {
        "message": "Upload Successful",
        "filename": file.filename,
        "path": str(path)
    }
