# AcousticSpace Deepfake Detection - Backend

## Overview

This backend is built using FastAPI. It provides APIs for uploading audio files, checking server health, and predicting whether an audio file is real or deepfake.

---

## Technologies Used

- Python 3.x
- FastAPI
- Uvicorn

---

## Installation

Create a virtual environment:

```bash
python3 -m venv venv
```

Activate the virtual environment:

**Linux/macOS**

```bash
source venv/bin/activate
```

**Windows**

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Running the Server

Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

The backend will run at:

- http://127.0.0.1:8000

Swagger UI:

- http://127.0.0.1:8000/docs

ReDoc:

- http://127.0.0.1:8000/redoc

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Check backend status |
| POST | `/upload` | Upload an audio file |
| POST | `/predict` | Predict whether an uploaded audio file is real or deepfake |

---

## Project Structure

```
backend/
├── app/
│   ├── api/
│   ├── core/
│   ├── schemas/
│   ├── services/
│   ├── utils/
│   └── main.py
├── uploads/
├── requirements.txt
└── README.md
```

---

## Notes

- Supported formats: `.wav`, `.mp3`, `.flac`, `.ogg`, `.m4a`
- Maximum upload size: **20 MB**
- Uploaded files are stored using unique UUID filenames.
