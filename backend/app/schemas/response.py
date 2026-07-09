from pydantic import BaseModel


class UploadResponse(BaseModel):
    message: str
    filename: str
    path: str

class PredictionResponse(BaseModel):
    prediction: str
    confidence: float
