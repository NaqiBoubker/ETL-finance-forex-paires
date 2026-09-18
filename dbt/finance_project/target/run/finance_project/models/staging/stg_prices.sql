
  create or replace   view MARKET_DB.ANALYTICS.stg_prices
  
   as (
    SELECT
    date,
    open,
    high,
    low,
    close,
    symbol
FROM MARKET_DB.RAW.raw_prices
  );

