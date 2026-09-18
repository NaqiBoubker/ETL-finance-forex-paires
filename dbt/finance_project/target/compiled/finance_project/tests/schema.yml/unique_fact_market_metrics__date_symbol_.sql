
    
    

select
    (date || '-' || symbol) as unique_field,
    count(*) as n_records

from MARKET_DB.ANALYTICS.fact_market_metrics
where (date || '-' || symbol) is not null
group by (date || '-' || symbol)
having count(*) > 1


