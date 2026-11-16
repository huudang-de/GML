SELECT 
    to_char(posting_date, 'YYYY-MM') AS period,
    SUM(ending_debit_balance) AS value
FROM ai_views.ai_v_cong_no
WHERE ar_ap_type = 'AR'
GROUP BY 1
ORDER BY 1;
