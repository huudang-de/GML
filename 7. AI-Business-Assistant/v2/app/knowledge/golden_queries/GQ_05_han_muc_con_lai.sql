SELECT SUM(granted_limit) - SUM(principal_balance)
FROM ai_views.ai_v_no_vay
WHERE record_type = 'credit_limit';
