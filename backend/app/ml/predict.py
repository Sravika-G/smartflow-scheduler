import os
import joblib
import pandas as pd

from app.ml.features import make_features

MODEL_PATH = os.getenv("MODEL_PATH", "app/ml/model.pkl")

def load_model():
    if not os.path.exists(MODEL_PATH):
        return None
    return joblib.load(MODEL_PATH)

def predict_runtime_ms(model, job_type: str, priority: int, attempts: int, payload_str: str | None) -> int | None:
    if model is None:
        return None
    feats = make_features(job_type, priority, attempts, payload_str)
    Xdf = pd.DataFrame([feats])
    pred = model.predict(Xdf)[0]
    # clamp to non-negative int
    return max(0, int(pred))