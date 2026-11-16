SELECT 
    to_char(COALESCE(as_of_date, posting_date), 'YYYY-MM') AS period,
    SUM(principal_balance) / NULLIF(SUM(granted_limit), 0) AS value
FROM ai_views.ai_v_no_vay
WHERE record_type = 'credit_limit'
GROUP BY 1
ORDER BY 1;
