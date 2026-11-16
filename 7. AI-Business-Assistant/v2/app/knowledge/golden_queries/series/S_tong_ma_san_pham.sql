WITH max_monthly AS (
    SELECT 
        to_char(tx_date, 'YYYY-MM') AS period,
        MAX(tx_date) AS max_tx_date
    FROM ai_views.ai_v_ton_kho
    WHERE record_type = 'balance'
    GROUP BY 1
)
SELECT 
    m.period,
    COUNT(DISTINCT t.product_code) AS value
FROM max_monthly m
JOIN ai_views.ai_v_ton_kho t 
  ON t.tx_date = m.max_tx_date
 AND t.record_type = 'balance'
 AND t.quantity > 0
GROUP BY 1
ORDER BY 1;
