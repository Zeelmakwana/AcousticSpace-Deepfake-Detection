from fastapi import FastAPI

app = FastAPI(
    title="AcousticSpace API",
    version="1.0.0"
)

@app.get("/")
def home():
    return {
        "message": "AcousticSpace Backend is Running"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }
