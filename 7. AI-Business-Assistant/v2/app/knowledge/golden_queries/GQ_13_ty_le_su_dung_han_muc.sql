SELECT SUM(principal_balance) / SUM(granted_limit)
FROM ai_views.ai_v_no_vay
WHERE record_type = 'credit_limit';
