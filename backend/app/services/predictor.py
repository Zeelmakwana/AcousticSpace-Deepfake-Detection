import random

def predict_audio(file_path: str):
    """
    Dummy prediction.
    Replace this with the ML model later.
    """

    labels = ["Real", "Fake"]

    return {
        "prediction": random.choice(labels),
        "confidence": round(random.uniform(0.80, 0.99), 2)
    }
