SELECT 
    to_char(tx_date, 'YYYY-MM') AS period,
    SUM(quantity) AS value
FROM ai_views.ai_v_ton_kho
WHERE record_type = 'balance'
GROUP BY 1
ORDER BY 1;
