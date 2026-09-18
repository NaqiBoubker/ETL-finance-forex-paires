SELECT
    date,
    symbol,
    return,

    -- 5-day volatility
    STDDEV(return) OVER (
        PARTITION BY symbol 
        ORDER BY date 
        ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
    ) AS vol_5d,

    -- 20-day volatility
    STDDEV(return) OVER (
        PARTITION BY symbol 
        ORDER BY date 
        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
    ) AS vol_20d

FROM ANALYTICS.int_returns