SELECT COALESCE((SELECT SUM(current_period_amount) FROM ai_views.ai_v_bctc WHERE item_code = 'B02-DN_10' AND report_type = 'B02-DN' AND reporting_date >= '2026-01-01'), 0) /
       NULLIF((SELECT AVG(ending_debit_balance) FROM ai_views.ai_v_cong_no WHERE ar_ap_type = 'AR' AND partner_group IN ('Khách hàng', 'Khách hàng/ nhà cung cấp') AND rn = 1), 0);
