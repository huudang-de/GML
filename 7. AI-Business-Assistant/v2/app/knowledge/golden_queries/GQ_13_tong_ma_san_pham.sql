SELECT COUNT(DISTINCT product_code)
FROM ai_views.ai_v_ton_kho
WHERE record_type = 'balance'
  AND tx_date = (SELECT MAX(tx_date) FROM ai_views.ai_v_ton_kho WHERE record_type = 'balance')
  AND quantity > 0;
