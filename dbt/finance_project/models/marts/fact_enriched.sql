SELECT
    f.*,
    d.asset_name,
    d.base_currency,
    d.quote_currency,
    d.type

FROM {{ ref('fact_market_metrics') }} f
LEFT JOIN {{ ref('dim_asset') }} d
    ON f.symbol = d.symbol