SELECT SUM(credit_balance)
FROM ai_views.ai_v_no_vay
WHERE record_type = 'ledger_balance'
  AND (account_no LIKE '34111%' OR account_no LIKE '34113%' OR account_no LIKE '34114%')
  AND rn = 1;
