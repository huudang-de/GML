SELECT SUM(debit_amount)
FROM ai_views.ai_v_dong_tien
WHERE reciprocal_account LIKE '515%';
