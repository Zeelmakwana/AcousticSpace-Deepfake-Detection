from fastapi import APIRouter

router = APIRouter(tags=["Health"])

@router.get("/")
def home():
    return {
        "message": "AcousticSpace Backend is Running"
    }

@router.get(
    "/health",
    summary="Health Check",
    description="Check whether the backend service is running."
)
def health():
    return {
        "status": "healthy",
        "service": "AcousticSpace API",
        "version": "1.0.0"
    }
