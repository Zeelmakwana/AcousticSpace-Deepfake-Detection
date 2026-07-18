from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.upload import router as upload_router
from app.api.prediction import router as prediction_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AcousticSpace API",
    version="1.0.0"
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(upload_router, prefix="/api/v1")
app.include_router(prediction_router, prefix="/api/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # We'll restrict this later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
