SELECT
    date,
    symbol,
    vol_20d,

    CASE
        WHEN vol_20d > 0.007 THEN 'HIGH_VOL'   -- above P75 + buffer → avoid
        WHEN vol_20d < 0.002 THEN 'LOW_VOL'    -- below absolute min → no trade
        ELSE 'NORMAL'                           -- everything else → trade normally
    END AS vol_regime

FROM {{ ref('int_volatility') }}