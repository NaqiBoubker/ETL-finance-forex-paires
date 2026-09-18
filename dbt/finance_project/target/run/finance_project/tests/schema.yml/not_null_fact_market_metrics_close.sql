
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select close
from MARKET_DB.ANALYTICS.fact_market_metrics
where close is null



  
  
      
    ) dbt_internal_test