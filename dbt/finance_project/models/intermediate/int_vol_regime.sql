SELECT
    date,
    symbol,
    vol_20d,

    CASE
        WHEN vol_20d > 0.01 THEN 'HIGH_VOL'
        WHEN vol_20d < 0.005 THEN 'LOW_VOL'
        ELSE 'NORMAL'
    END AS vol_regime

FROM {{ ref('int_volatility') }}