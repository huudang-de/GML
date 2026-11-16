SELECT 
    to_char(posting_date, 'YYYY-MM') AS period,
    SUM(debit_amount) AS value
FROM ai_views.ai_v_dong_tien
WHERE is_external_cashflow = TRUE
GROUP BY 1
ORDER BY 1;
