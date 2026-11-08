SELECT SUM(ending_credit_balance)
FROM ai_views.ai_v_cong_no
WHERE ar_ap_type = 'AP'
  AND partner_group IN ('Nhà cung cấp', 'Khách hàng/ nhà cung cấp')
  AND rn = 1;
