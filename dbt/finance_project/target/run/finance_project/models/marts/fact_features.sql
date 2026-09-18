
  
    

        create or replace transient table MARKET_DB.ANALYTICS.fact_features
         as
        (SELECT
    f.date,
    f.symbol,
    f.close,
    f.return,
    f.vol_5d,
    f.vol_20d,
    ma.ma_5d,
    ma.ma_20d,
    r.rsi_14

FROM MARKET_DB.ANALYTICS.fact_market_metrics f

LEFT JOIN MARKET_DB.ANALYTICS.int_moving_avg ma
    ON f.date = ma.date AND f.symbol = ma.symbol

LEFT JOIN MARKET_DB.ANALYTICS.int_rsi r
    ON f.date = r.date AND f.symbol = r.symbol
        );
      
  