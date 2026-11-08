SELECT ending_balance
FROM ai_views.ai_v_bctc
WHERE item_code = 'B01-DN_110'
  AND report_type = 'B01-DN'
  AND reporting_date = (SELECT MAX(reporting_date) FROM ai_views.ai_v_bctc WHERE report_type = 'B01-DN');
