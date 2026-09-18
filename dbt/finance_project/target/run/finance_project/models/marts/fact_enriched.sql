
  
    

        create or replace transient table MARKET_DB.ANALYTICS.fact_enriched
         as
        (SELECT
    f.*,
    d.asset_name,
    d.base_currency,
    d.quote_currency,
    d.type

FROM MARKET_DB.ANALYTICS.fact_market_metrics f
LEFT JOIN MARKET_DB.ANALYTICS.dim_asset d
    ON f.symbol = d.symbol
        );
      
  