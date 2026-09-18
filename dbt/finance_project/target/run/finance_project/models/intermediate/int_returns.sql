
  
    

        create or replace transient table MARKET_DB.ANALYTICS.int_returns
         as
        (SELECT
    date,
    symbol,
    close,
    LAG(close) OVER (PARTITION BY symbol ORDER BY date) AS prev_close,
    (close - LAG(close) OVER (PARTITION BY symbol ORDER BY date)) 
        / LAG(close) OVER (PARTITION BY symbol ORDER BY date) AS return
FROM ANALYTICS.stg_prices
        );
      
  