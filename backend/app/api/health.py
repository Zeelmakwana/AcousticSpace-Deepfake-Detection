from fastapi import APIRouter

router = APIRouter(tags=["Health"])

@router.get("/")
def home():
    return {
        "message": "AcousticSpace Backend is Running"
    }

@router.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "AcousticSpace API",
        "version": "1.0.0"
    }
