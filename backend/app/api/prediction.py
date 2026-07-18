from fastapi import APIRouter, UploadFile, File, HTTPException
from app.schemas.response import PredictionResponse
from app.services.file_service import save_uploaded_file
from app.services.predictor import predict_audio

router = APIRouter(tags=["Prediction"])

@router.post("/predict", response_model=PredictionResponse)
async def predict(file: UploadFile = File(...)):
    try:
        path = save_uploaded_file(file)
        return predict_audio(str(path))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
