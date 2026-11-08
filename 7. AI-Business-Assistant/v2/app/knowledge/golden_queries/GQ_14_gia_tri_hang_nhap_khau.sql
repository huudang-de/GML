SELECT SUM(total_value)
FROM ai_views.ai_v_ton_kho
WHERE record_type = 'inward'
  AND exchange_rate > 1;
