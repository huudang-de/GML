SELECT COUNT(*)
FROM ai_views.ai_v_cong_no
WHERE ar_ap_type = 'AR'
  AND partner_group IN ('Khách hàng', 'Khách hàng/ nhà cung cấp')
  AND rn = 1
  AND ending_debit_balance > 0;
