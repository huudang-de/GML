SELECT SUM(principal_balance) / NULLIF(SUM(granted_limit), 0)
FROM ai_views.ai_v_no_vay
WHERE record_type = 'credit_limit';
