SELECT COALESCE((SELECT SUM(current_period_amount) FROM ai_views.ai_v_bctc WHERE item_code = 'B02-DN_11' AND report_type = 'B02-DN' AND month = (SELECT MAX(month) FROM ai_views.ai_v_bctc WHERE report_type = 'B02-DN')), 0) /
       NULLIF((SELECT SUM(total_value) FROM ai_views.ai_v_ton_kho WHERE record_type = 'balance'), 0);
