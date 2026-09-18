
  
    

        create or replace transient table MARKET_DB.ANALYTICS.int_moving_avg
         as
        (SELECT
    date,
    symbol,
    close,
    AVG(close) OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) AS ma_5d,
    AVG(close) OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS ma_20d
FROM MARKET_DB.ANALYTICS.stg_prices
        );
      
  