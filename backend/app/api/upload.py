from fastapi import APIRouter, UploadFile, File
from app.schemas.response import UploadResponse
from app.services.file_service import save_uploaded_file
from app.utils.logger import logger

router = APIRouter(tags=["Upload"])

@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload an audio file",
    description="Upload an audio file for deepfake detection."
)
async def upload(file: UploadFile = File(...)):
    logger.info(f"Uploaded file: {file.filename}")

    path = save_uploaded_file(file)

    return UploadResponse(
    success=True,
    message="Upload successful",
    data={
        "filename": file.filename,
        "path": str(path)
    }
)
