
  
    

        create or replace transient table MARKET_DB.ANALYTICS.fact_signals
         as
        (SELECT
    f.*,

    -- Trend signal (MA crossover)
    CASE
        WHEN f.ma_5d > f.ma_20d THEN 'BULLISH'
        WHEN f.ma_5d < f.ma_20d THEN 'BEARISH'
        ELSE 'NEUTRAL'
    END AS trend_signal,

    -- RSI signal (momentum)
    CASE
        WHEN f.rsi_14 < 30 THEN 'OVERSOLD'
        WHEN f.rsi_14 > 70 THEN 'OVERBOUGHT'
        ELSE 'NEUTRAL'
    END AS rsi_signal,

    -- Combined trading signal
    CASE
        WHEN vr.vol_regime = 'HIGH_VOL' THEN 'AVOID'
        WHEN vr.vol_regime = 'LOW_VOL' THEN 'NO_TRADE'

        WHEN f.ma_5d > f.ma_20d AND f.rsi_14 < 30 THEN 'STRONG_BUY'
        WHEN f.ma_5d < f.ma_20d AND f.rsi_14 > 70 THEN 'STRONG_SELL'
        WHEN f.ma_5d > f.ma_20d THEN 'BUY'
        WHEN f.ma_5d < f.ma_20d THEN 'SELL'
        ELSE 'HOLD'
    END AS trading_signal

FROM MARKET_DB.ANALYTICS.fact_features f

LEFT JOIN MARKET_DB.ANALYTICS.int_vol_regime vr
    ON f.date = vr.date AND f.symbol = vr.symbol
        );
      
  