WITH fact_positions AS (
    SELECT
        date,
        symbol,
        return,
        trading_signal,
        CASE
            WHEN trading_signal IN ('BUY', 'STRONG_BUY') THEN 1
            WHEN trading_signal IN ('SELL', 'STRONG_SELL') THEN -1
            ELSE 0
        END AS position
    FROM MARKET_DB.ANALYTICS.fact_signals
),

base AS (
    SELECT
        *,
        LAG(position) OVER (PARTITION BY symbol ORDER BY date) AS lagged_position,

        -- Detect trade entry/exit (position changed)
        CASE
            WHEN position != LAG(position) OVER (PARTITION BY symbol ORDER BY date)
            THEN 1 ELSE 0
        END AS trade_occurred

    FROM fact_positions
),

with_costs AS (
    SELECT
        *,
        -- 2 pips per side = 0.0002 (typical FX spread)
        -- Only deduct cost on days where position changed
        lagged_position * return
        - (trade_occurred * 0.0004) AS strategy_return
        --                  ^^^^^^
        --          round trip cost (entry + exit)

    FROM base
),

cum_returns AS (
    SELECT
        *,
        EXP(
            SUM(
                CASE
                    WHEN strategy_return > -1
                    THEN LN(1 + strategy_return)
                    ELSE NULL
                END
            ) OVER (
                PARTITION BY symbol
                ORDER BY date
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )
        ) - 1 AS cumulative_return
    FROM with_costs
),

drawdown_calc AS (
    SELECT
        *,
        MAX(cumulative_return) OVER (
            PARTITION BY symbol
            ORDER BY date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS running_max
    FROM cum_returns
),

final AS (
    SELECT
        *,
        (cumulative_return / NULLIF(running_max, 0)) - 1 AS drawdown,
        CASE
            WHEN lagged_position != 0 AND strategy_return > 0 THEN 1
            ELSE 0
        END AS win_flag
    FROM drawdown_calc
)

SELECT
    *,
    (
        AVG(strategy_return) OVER (
            PARTITION BY symbol
            ORDER BY date
            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
        )
        /
        NULLIF(
            STDDEV(strategy_return) OVER (
                PARTITION BY symbol
                ORDER BY date
                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
            ), 0
        )
    ) * SQRT(252) AS sharpe_annualized

FROM final