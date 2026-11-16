WITH ranked AS (
    SELECT 
        to_char(posting_date, 'YYYY-MM') AS period,
        account_no,
        credit_balance,
        ROW_NUMBER() OVER (
            PARTITION BY account_no, to_char(posting_date, 'YYYY-MM') 
            ORDER BY posting_date DESC, tx_id DESC
        ) as rn
    FROM ai_views.ai_v_no_vay
    WHERE record_type = 'ledger_balance'
      AND account_no LIKE '34112%'
)
SELECT period, SUM(credit_balance) AS value
FROM ranked
WHERE rn = 1
GROUP BY period
ORDER BY period;
