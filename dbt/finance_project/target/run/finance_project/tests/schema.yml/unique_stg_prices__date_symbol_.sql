
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    (date || '-' || symbol) as unique_field,
    count(*) as n_records

from MARKET_DB.ANALYTICS.stg_prices
where (date || '-' || symbol) is not null
group by (date || '-' || symbol)
having count(*) > 1



  
  
      
    ) dbt_internal_test