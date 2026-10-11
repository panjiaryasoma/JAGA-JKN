"""
Defines 3 operational candidate classification algorithms configured with
class_weight='balanced' to handle class imbalance.
"""

import sys
from pathlib import Path

import lightgbm as lgb
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipelines.ml.config import MODEL_SEED


def get_models() -> dict:
    
    return {
        "Logistic Regression": LogisticRegression(
            class_weight="balanced",
            C=0.1,
            max_iter=1000,
            solver="lbfgs",
            random_state=MODEL_SEED,
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=300,
            max_depth=10,
            min_samples_leaf=10,
            class_weight="balanced",
            random_state=MODEL_SEED,
            n_jobs=-1,
        ),
        "LightGBM": lgb.LGBMClassifier(
            n_estimators=500,
            learning_rate=0.05,
            num_leaves=31,
            class_weight="balanced",
            random_state=MODEL_SEED,
            n_jobs=-1,
            verbose=-1,
        ),
    }
