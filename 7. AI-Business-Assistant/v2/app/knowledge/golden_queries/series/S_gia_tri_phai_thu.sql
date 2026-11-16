WITH ranked AS (
    SELECT
        to_char(posting_date, 'YYYY-MM') AS period,
        partner_code,
        ending_debit_balance,
        ROW_NUMBER() OVER (
            PARTITION BY partner_code, to_char(posting_date, 'YYYY-MM')
            ORDER BY posting_date DESC, tx_id DESC
        ) AS rn
    FROM ai_views.ai_v_cong_no
    WHERE ar_ap_type = 'AR'
      AND partner_group IN ('Khách hàng', 'Khách hàng/ nhà cung cấp')
)
SELECT period, SUM(ending_debit_balance) AS value
FROM ranked
WHERE rn = 1
GROUP BY period
ORDER BY period;
