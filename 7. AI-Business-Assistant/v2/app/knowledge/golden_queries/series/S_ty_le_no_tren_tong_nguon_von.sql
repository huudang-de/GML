SELECT 
    to_char(reporting_date, 'YYYY-MM') AS period,
    MAX(CASE WHEN item_code = 'B01-DN_300' THEN ending_balance END) /
    NULLIF(MAX(CASE WHEN item_code = 'B01-DN_440' THEN ending_balance END), 0) AS value
FROM ai_views.ai_v_bctc
WHERE report_type = 'B01-DN'
  AND item_code IN ('B01-DN_300', 'B01-DN_440')
GROUP BY reporting_date
ORDER BY reporting_date;
