SELECT SUM(credit_balance)
FROM ai_views.ai_v_no_vay
WHERE record_type = 'ledger_balance'
  AND account_no LIKE '34112%'
  AND rn = 1;
