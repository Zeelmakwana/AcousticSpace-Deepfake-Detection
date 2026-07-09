from fastapi import APIRouter
from fastapi import UploadFile, File
from app.services.file_service import save_uploaded_file
from app.services.predictor import predict_audio
from app.utils.logger import logger
from app.schemas.response import UploadResponse, PredictionResponse
from fastapi import HTTPException

router = APIRouter()

@router.get("/")
def home():
    return {"message": "AcousticSpace Backend is Running"}

@router.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "AcousticSpace API",
        "version": "1.0.0"
    }
    
@router.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
  
    logger.info(f"Uploaded file: {file.filename}")


    path = save_uploaded_file(file)

    return {
        "message": "Upload Successful",
        "filename": file.filename,
        "path": str(path)
    }
    
@router.post("/predict", response_model=PredictionResponse)
async def predict(file: UploadFile = File(...)):

    try:

        path = save_uploaded_file(file)

        result = predict_audio(str(path))

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
