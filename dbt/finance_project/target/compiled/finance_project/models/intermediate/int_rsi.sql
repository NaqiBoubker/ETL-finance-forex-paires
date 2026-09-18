WITH price_changes AS (
    SELECT
        date,
        symbol,
        close,
        close - LAG(close) OVER (
            PARTITION BY symbol ORDER BY date
        ) AS change
    FROM MARKET_DB.ANALYTICS.stg_prices
),

gains_losses AS (
    SELECT
        date,
        symbol,
        close,
        CASE WHEN change > 0 THEN change ELSE 0 END AS gain,
        CASE WHEN change < 0 THEN ABS(change) ELSE 0 END AS loss
    FROM price_changes
),

avg_gains_losses AS (
    SELECT
        date,
        symbol,
        close,

        AVG(gain) OVER (
            PARTITION BY symbol
            ORDER BY date
            ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
        ) AS avg_gain,

        AVG(loss) OVER (
            PARTITION BY symbol
            ORDER BY date
            ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
        ) AS avg_loss

    FROM gains_losses
)

SELECT
    date,
    symbol,
    close,

    CASE
        WHEN avg_loss = 0 THEN 100
        ELSE 100 - (100 / (1 + (avg_gain / avg_loss)))
    END AS rsi_14

FROM avg_gains_losses