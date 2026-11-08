SELECT COUNT(*) FROM (
    SELECT invoice_no
    FROM ai_views.ai_v_cong_no
    WHERE ar_ap_type = 'AR'
      AND partner_group IN ('Khách hàng', 'Khách hàng/ nhà cung cấp')
      AND invoice_no IS NOT NULL
      AND invoice_no != ''
    GROUP BY invoice_no
    HAVING SUM(debit_amount - credit_amount) > 0
) t;
