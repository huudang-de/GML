SELECT (SELECT SUM(granted_limit) FROM ai_views.ai_v_no_vay WHERE record_type = 'credit_limit') /
       NULLIF((SELECT SUM(appraised_value) FROM ai_views.ai_v_no_vay WHERE record_type = 'collateral'), 0);
