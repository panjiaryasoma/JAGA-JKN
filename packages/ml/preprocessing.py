"""Fitted preprocessing shared by offline evaluation and artifact inference."""

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OrdinalEncoder, StandardScaler

from pipelines.configure.config import ALL_FEATURES, CATEGORICAL_FEATURES


def validate_feature_frame(frame):
    if list(frame.columns) != ALL_FEATURES:
        raise ValueError("Feature schema/order differs from the model contract")
    if frame.empty:
        raise ValueError("Empty feature matrix")
    nums = frame.drop(columns=CATEGORICAL_FEATURES).to_numpy(dtype=float)
    if np.isinf(nums).any():
        raise ValueError("Infinite numeric feature")


def build_preprocessor(train):
    validate_feature_frame(train)
    cat_cols = list(CATEGORICAL_FEATURES)
    num_cols = [c for c in ALL_FEATURES if c not in cat_cols]
    encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    encoder.fit(train[cat_cols].fillna("MISSING").astype(str))
    imputer = SimpleImputer(strategy="median", keep_empty_features=True)
    imputed = imputer.fit_transform(train[num_cols])
    scaler = StandardScaler().fit(imputed)
    return {
        "cat_cols": cat_cols,
        "num_cols": num_cols,
        "cat_encoder": encoder,
        "num_imputer": imputer,
        "num_scaler": scaler,
    }


def transform_features(frame, preprocessor):
    validate_feature_frame(frame)
    p = preprocessor
    categorical = p["cat_encoder"].transform(frame[p["cat_cols"]].fillna("MISSING").astype(str))
    numeric = p["num_scaler"].transform(p["num_imputer"].transform(frame[p["num_cols"]]))
    return pd.DataFrame(
        np.hstack([numeric, categorical]), index=frame.index, columns=p["num_cols"] + p["cat_cols"]
    )
