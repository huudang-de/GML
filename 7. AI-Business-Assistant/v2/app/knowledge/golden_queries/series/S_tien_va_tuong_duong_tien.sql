SELECT 
    to_char(reporting_date, 'YYYY-MM') AS period,
    SUM(ending_balance) AS value
FROM ai_views.ai_v_bctc
WHERE report_type = 'B01-DN'
  AND item_code = 'B01-DN_110'
GROUP BY reporting_date
ORDER BY reporting_date;
