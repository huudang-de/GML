SELECT 
    to_char(COALESCE(as_of_date, posting_date), 'YYYY-MM') AS period,
    SUM(granted_limit) AS value
FROM ai_views.ai_v_no_vay
WHERE record_type = 'credit_limit'
GROUP BY 1
ORDER BY 1;
