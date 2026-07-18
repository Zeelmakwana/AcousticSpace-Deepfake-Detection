from fastapi import APIRouter, UploadFile, File, HTTPException
from app.schemas.response import PredictionResponse
from app.services.file_service import save_uploaded_file
from app.services.predictor import predict_audio

router = APIRouter(tags=["Prediction"])

@router.post(
    "/predict",
    response_model=PredictionResponse,
    summary="Predict audio authenticity",
    description="Predict whether the uploaded audio is real or deepfake."
)
async def predict(file: UploadFile = File(...)):
    path = save_uploaded_file(file)

    result = predict_audio(str(path))

    return PredictionResponse(
        success=True,
        message="Prediction completed",
        data=result
    )
