from pydantic import BaseModel
from typing import Any, Optional


class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None


class UploadResponse(APIResponse):
    pass


class PredictionResponse(APIResponse):
    pass
