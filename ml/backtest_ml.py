import sys
import os

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

import pandas as pd
import numpy as np
import snowflake.connector
import matplotlib.pyplot as plt

from ingestion.utils.helpers import get_snowflake_config

SYMBOLS = ["EURUSD", "GBPUSD", "EURGBP", "USDCHF", "EURAUD"]
COST_PER_TRADE = 0.0004

results = []

for SYMBOL in SYMBOLS:
    conn = snowflake.connector.connect(**get_snowflake_config())
    df = pd.read_sql(f"""
        SELECT f.date, f.symbol, f.return, m.regime, m.ml_signal
        FROM ANALYTICS.FACT_FEATURES f
        JOIN ANALYTICS.FACT_ML_SIGNALS m
            ON f.date = m.date AND f.symbol = m.symbol
        WHERE f.symbol = '{SYMBOL}'
        ORDER BY f.date
    """, conn)
    conn.close()

    df.columns = df.columns.str.lower()
    df["position"] = np.where(df["ml_signal"] == "BUY", 1,
                     np.where(df["ml_signal"] == "SELL", -1, 0))

    # Lagged position — no lookahead bias
    df["lagged_position"] = df["position"].shift(1)

    # Detect trade
    df["trade"] = (df["position"] != df["position"].shift(1)).astype(int)

    # Strategy return with transaction costs
    df["strategy_return"] = (
        df["lagged_position"] * df["return"]
        - df["trade"] * COST_PER_TRADE
    )

    df["cumulative_return"] = (1 + df["strategy_return"]).cumprod() - 1

    total_return = df["cumulative_return"].iloc[-1]
    sharpe       = (df["strategy_return"].mean() / df["strategy_return"].std()) * np.sqrt(252)
    volatility   = df["strategy_return"].std() * np.sqrt(252)
    win_rate     = (df["strategy_return"] > 0).mean()
    max_dd       = (df["cumulative_return"] - df["cumulative_return"].cummax()).min()

    results.append({
        "symbol":        SYMBOL,
        "total_return":  total_return,
        "sharpe":        sharpe,
        "volatility":    volatility,
        "win_rate":      win_rate,
        "max_drawdown":  max_dd
    })

    print(f"\n===== {SYMBOL} =====")
    print(f"Total Return:  {total_return:.2%}")
    print(f"Sharpe Ratio:  {sharpe:.2f}")
    print(f"Volatility:    {volatility:.2%}")
    print(f"Win Rate:      {win_rate:.2%}")
    print(f"Max Drawdown:  {max_dd:.2%}")

# Summary table
print("\n========== SUMMARY ==========")
results_df = pd.DataFrame(results).set_index("symbol")
print(results_df.to_string(float_format="{:.4f}".format))

# Plot all
fig, axes = plt.subplots(len(SYMBOLS), 1, figsize=(14, 16), sharex=True)
for i, SYMBOL in enumerate(SYMBOLS):
    conn = snowflake.connector.connect(**get_snowflake_config())
    df = pd.read_sql(f"""
        SELECT f.date, f.return, m.ml_signal
        FROM ANALYTICS.FACT_FEATURES f
        JOIN ANALYTICS.FACT_ML_SIGNALS m
            ON f.date = m.date AND f.symbol = m.symbol
        WHERE f.symbol = '{SYMBOL}' ORDER BY f.date
    """, conn)
    conn.close()
    df.columns = df.columns.str.lower()
    df["position"] = np.where(df["ml_signal"] == "BUY", 1,
                     np.where(df["ml_signal"] == "SELL", -1, 0))
    df["trade"]    = (df["position"] != df["position"].shift(1)).astype(int)
    df["strategy_return"] = df["position"].shift(1) * df["return"] - df["trade"] * COST_PER_TRADE
    df["cumulative_return"] = (1 + df["strategy_return"]).cumprod() - 1
    axes[i].plot(df["date"], df["cumulative_return"], linewidth=1.5)
    axes[i].set_title(SYMBOL, fontsize=11)
    axes[i].set_ylabel("Cum Return")
    axes[i].grid(True, alpha=0.3)

plt.suptitle("HMM Strategy — All Pairs (with transaction costs)", fontsize=13)
plt.tight_layout()
plt.show()