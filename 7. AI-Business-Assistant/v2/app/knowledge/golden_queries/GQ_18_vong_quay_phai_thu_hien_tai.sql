SELECT (SELECT SUM(current_period_amount) FROM ai_views.ai_v_bctc WHERE item_code = 'B02-DN_10' AND report_type = 'B02-DN' AND month = (SELECT MAX(month) FROM ai_views.ai_v_bctc WHERE report_type = 'B02-DN')) /
       NULLIF((SELECT SUM(ending_debit_balance) FROM ai_views.ai_v_cong_no WHERE ar_ap_type = 'AR' AND partner_group IN ('Khách hàng', 'Khách hàng/ nhà cung cấp') AND rn = 1), 0);
