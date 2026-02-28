import os
import joblib
import numpy as np

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import GradientBoostingRegressor

from app.db.database import SessionLocal
from app.db.models import Job
from app.ml.features import make_features

MODEL_PATH = os.getenv("MODEL_PATH", "app/ml/model.pkl")

def train():
    db = SessionLocal()
    try:
        rows = (
            db.query(Job)
            .filter(Job.status == "completed")
            .filter(Job.runtime_ms != None)
            .all()
        )

        if len(rows) < 10:
            print(f"Not enough training data: {len(rows)} completed jobs with runtime_ms. Need at least 10.")
            return

        X = []
        y = []
        for r in rows:
            feats = make_features(r.type, r.priority, r.attempts, r.payload)
            X.append(feats)
            y.append(r.runtime_ms)

        # Build arrays
        # We'll use dicts -> convert via simple list of dicts
        # Pipeline handles encoding for "type"
        import pandas as pd
        Xdf = pd.DataFrame(X)
        yarr = np.array(y)

        pre = ColumnTransformer(
            transformers=[
                ("type", OneHotEncoder(handle_unknown="ignore"), ["type"]),
                ("num", "passthrough", ["priority", "attempts", "payload_size"]),
            ]
        )

        model = GradientBoostingRegressor()
        pipe = Pipeline(steps=[("pre", pre), ("model", model)])

        pipe.fit(Xdf, yarr)

        joblib.dump(pipe, MODEL_PATH)
        print(f"Saved model to {MODEL_PATH}. Trained on {len(rows)} rows.")
    finally:
        db.close()

if __name__ == "__main__":
    train()