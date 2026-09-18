import numpy as np
import pandas as pd
import joblib
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import StandardScaler
from ml.features.feature_engineering import load_features, build_features

N_STATES  = 3
N_ITER    = 1000
MODEL_DIR = os.path.join(os.path.dirname(__file__), "saved")

def train(symbol):
    print(f"Training HMM for {symbol}...")

    df = load_features(symbol)
    X, df = build_features(df)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = GaussianHMM(
        n_components=N_STATES,
        covariance_type="full",
        n_iter=N_ITER,
        random_state=42
    )
    model.fit(X_scaled)

    regimes = model.predict(X_scaled)
    df["regime_raw"] = regimes

    regime_returns = df.groupby("regime_raw")["RETURN"].mean().sort_values()
    label_map = {
        regime_returns.index[0]: "BEARISH",
        regime_returns.index[1]: "NEUTRAL",
        regime_returns.index[2]: "BULLISH",
    }
    df["regime"] = df["regime_raw"].map(label_map)

    probs = model.predict_proba(X_scaled)
    bearish_idx = regime_returns.index[0]
    neutral_idx = regime_returns.index[1]
    bullish_idx = regime_returns.index[2]

    df["p_bearish"] = probs[:, bearish_idx]
    df["p_neutral"] = probs[:, neutral_idx]
    df["p_bullish"] = probs[:, bullish_idx]

    df["ml_signal"] = df.apply(lambda r:
        "BUY"  if r["p_bullish"] > 0.6 else
        "SELL" if r["p_bearish"] > 0.6 else
        "HOLD", axis=1
    )

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model,     f"{MODEL_DIR}/{symbol}_hmm.pkl")
    joblib.dump(scaler,    f"{MODEL_DIR}/{symbol}_scaler.pkl")
    joblib.dump(label_map, f"{MODEL_DIR}/{symbol}_labels.pkl")

    print(f"  -> Converged: {model.monitor_.converged}")
    print(f"  -> Regimes:\n{df['regime'].value_counts()}")
    print(f"  -> Signals:\n{df['ml_signal'].value_counts()}")

    return df, model, scaler

if __name__ == "__main__":
    SYMBOLS = ["EURUSD", "GBPUSD", "EURGBP", "USDCHF", "EURAUD"]
    for s in SYMBOLS:
        train(s)
    print("Done.")

