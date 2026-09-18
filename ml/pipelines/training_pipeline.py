import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

import numpy as np
import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas

from ingestion.utils.helpers import get_snowflake_config

SYMBOLS   = ["EURUSD", "GBPUSD", "EURGBP", "USDCHF", "EURAUD"]
MODEL_DIR = os.path.join(os.path.dirname(__file__), "../models/saved")
COST      = 0.0004


def save_backtest_to_snowflake(df, symbol):
    df = df.copy()
    df.columns = df.columns.str.lower()
    df = df.sort_values("date")

    # Position from ML signal
    df["position"]        = np.where(df["ml_signal"] == "BUY",  1,
                            np.where(df["ml_signal"] == "SELL", -1, 0))
    df["lagged_position"] = df["position"].shift(1)
    df["trade"]           = (df["position"] != df["position"].shift(1)).astype(int)

    # Strategy return with transaction costs
    df["strategy_return"] = (
        df["lagged_position"] * df["return"]
        - df["trade"] * COST
    )

    # Cumulative return
    df["cumulative_return"] = (1 + df["strategy_return"]).cumprod() - 1

    # Drawdown
    df["running_max"] = df["cumulative_return"].cummax()
    df["drawdown"]    = df["cumulative_return"] - df["running_max"]

    # Rolling Sharpe (20d annualized)
    df["sharpe_annualized"] = (
        df["strategy_return"].rolling(20).mean()
        / df["strategy_return"].rolling(20).std()
    ) * np.sqrt(252)

    # Win flag
    df["win_flag"] = (df["strategy_return"] > 0).astype(int)

    # Prepare output dataframe
    out = df[[
        "date", "symbol", "strategy_return", "cumulative_return",
        "running_max", "drawdown", "win_flag", "sharpe_annualized"
    ]].copy()

    # Uppercase columns for Snowflake
    out.columns = [c.upper() for c in out.columns]
    out["DATE"]   = pd.to_datetime(out["DATE"]).dt.date
    out["SYMBOL"] = symbol

    # Replace NaN with None
    out = out.where(pd.notnull(out), None)

    conn = snowflake.connector.connect(**get_snowflake_config())

    with conn.cursor() as cur:
        # Create table if not exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ANALYTICS.fact_ml_backtest (
                date              DATE,
                symbol            STRING,
                strategy_return   FLOAT,
                cumulative_return FLOAT,
                running_max       FLOAT,
                drawdown          FLOAT,
                win_flag          NUMBER,
                sharpe_annualized FLOAT
            )
        """)
        # Delete existing rows for this symbol
        cur.execute(
            f"DELETE FROM ANALYTICS.fact_ml_backtest WHERE symbol = '{symbol}'"
        )

    # Bulk insert
    write_pandas(
        conn, out,
        table_name="FACT_ML_BACKTEST",
        schema="ANALYTICS",
        database="MARKET_DB"
    )

    conn.close()
    print(f"  -> {len(out)} backtest rows saved for {symbol}")


def run():
    for symbol in SYMBOLS:
        try:
            # Load existing signals from Snowflake — no retraining
            conn = snowflake.connector.connect(**get_snowflake_config())
            df = pd.read_sql(f"""
                SELECT
                    f.date,
                    f.symbol,
                    f.return,
                    m.ml_signal,
                    m.regime,
                    m.p_bearish,
                    m.p_neutral,
                    m.p_bullish
                FROM ANALYTICS.FACT_FEATURES f
                JOIN ANALYTICS.FACT_ML_SIGNALS m
                    ON f.date = m.date
                   AND f.symbol = m.symbol
                WHERE f.symbol = '{symbol}'
                  AND f.return IS NOT NULL
                ORDER BY f.date
            """, conn)
            conn.close()

            print(f"Loaded {len(df)} rows for {symbol}")
            save_backtest_to_snowflake(df, symbol)

        except Exception as e:
            print(f"Failed for {symbol}: {e}")
            continue

    print("\nAll done.")


if __name__ == "__main__":
    run()