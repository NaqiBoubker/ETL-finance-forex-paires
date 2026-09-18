
  
    

        create or replace transient table MARKET_DB.ANALYTICS.fact_market_metrics
         as
        (SELECT
    p.date,
    p.symbol,
    p.close,
    v.return,
    v.vol_5d,
    v.vol_20d

FROM ANALYTICS.stg_prices p


LEFT JOIN ANALYTICS.int_volatility v
    ON p.date = v.date AND p.symbol = v.symbol
        );
      
  