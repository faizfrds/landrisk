"""Land-use change type classifier.

Per design doc: classify detected change into new_development / clearing /
wetland_loss / none. Training a real classifier needs labeled examples,
which are out of scope for this pass (the 300-parcel labeling effort is
explicitly deferred). This module ships with a rule-based NDVI-direction
fallback so the pipeline never hard-fails for lack of a trained model.
"""

from pathlib import Path
from typing import Literal

import joblib

ChangeType = Literal["new_development", "clearing", "wetland_loss", "none"]

MODEL_PATH = Path(__file__).parents[3] / "data" / "models" / "landuse_classifier.joblib"


def _rule_based_fallback(ndvi_before: float, ndvi_after: float, ndwi_after: float) -> ChangeType:
    ndvi_delta = ndvi_after - ndvi_before
    if ndwi_after > 0.3 and ndvi_delta < -0.2:
        return "wetland_loss"
    if ndvi_delta < -0.3:
        return "clearing"
    if ndvi_delta < -0.15:
        return "new_development"
    return "none"


def train(features_csv: str, labels_csv: str) -> None:
    """Train a small RandomForestClassifier on labeled examples.

    Not runnable without a labeled dataset -- structural stub for when the
    labeling effort happens (see backend/app/eval/README.md).
    """
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier

    features = pd.read_csv(features_csv)
    labels = pd.read_csv(labels_csv)
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(features, labels.values.ravel())
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)


def predict(feature_vector: dict) -> ChangeType:
    """Predict change type for one cell's feature vector.

    feature_vector keys: ndvi_before, ndvi_after, ndwi_after (at minimum --
    matches the rule-based fallback's inputs; a trained model may use more).
    """
    if MODEL_PATH.exists():
        model = joblib.load(MODEL_PATH)
        return model.predict([list(feature_vector.values())])[0]
    return _rule_based_fallback(
        feature_vector["ndvi_before"], feature_vector["ndvi_after"], feature_vector["ndwi_after"]
    )
