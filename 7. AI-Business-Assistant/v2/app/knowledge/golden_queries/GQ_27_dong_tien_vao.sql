SELECT SUM(debit_amount)
FROM ai_views.ai_v_dong_tien
WHERE is_external_cashflow = TRUE;
