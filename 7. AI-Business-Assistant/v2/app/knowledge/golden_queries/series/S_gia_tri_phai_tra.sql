WITH ranked AS (
    SELECT
        to_char(posting_date, 'YYYY-MM') AS period,
        partner_code,
        ending_credit_balance,
        ROW_NUMBER() OVER (
            PARTITION BY partner_code, to_char(posting_date, 'YYYY-MM')
            ORDER BY posting_date DESC, tx_id DESC
        ) AS rn
    FROM ai_views.ai_v_cong_no
    WHERE ar_ap_type = 'AP'
      AND partner_group IN ('Nhà cung cấp', 'Khách hàng/ nhà cung cấp')
)
SELECT period, SUM(ending_credit_balance) AS value
FROM ranked
WHERE rn = 1
GROUP BY period
ORDER BY period;
