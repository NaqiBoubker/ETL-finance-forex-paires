import pandas as pd
import numpy as np
import snowflake.connector
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from ingestion.utils.helpers import get_snowflake_config

def load_features(symbol: str) -> pd.DataFrame:
    conn = snowflake.connector.connect(**get_snowflake_config())
    df = pd.read_sql(f"""
        SELECT DATE, SYMBOL, CLOSE, RETURN, VOL_5D, VOL_20D, RSI_14,
               MA_5D, MA_20D
        FROM ANALYTICS.FACT_FEATURES
        WHERE SYMBOL = '{symbol}'
          AND RETURN  IS NOT NULL
          AND VOL_5D  IS NOT NULL
          AND VOL_20D IS NOT NULL
        ORDER BY DATE
    """, conn)
    conn.close()
    return df

def build_features(df: pd.DataFrame) -> np.ndarray:
    """
    Feature matrix for HMM:
        1. return        â†’ direction
        2. vol_5d        â†’ short-term risk
        3. vol_20d       â†’ long-term risk
        4. rsi_norm      â†’ momentum (normalized 0-1)
        5. ma_ratio      â†’ trend strength
    """
    df = df.copy()
    df["rsi_norm"]  = df["RSI_14"] / 100.0
    df["ma_ratio"]  = (df["MA_5D"] - df["MA_20D"]) / df["MA_20D"]

    features = ["RETURN", "VOL_5D", "VOL_20D", "rsi_norm", "ma_ratio"]
    X = df[features].values
    return X, df
