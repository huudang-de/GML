WITH LastRow AS (
    SELECT
        account_no,
        credit_balance,
        ROW_NUMBER() OVER (
            PARTITION BY account_no
            ORDER BY posting_date DESC, id DESC
        ) AS rn
    FROM FACT_CASHFLOW
    WHERE account_no IN ('34111', '34113', '34114')
)
SELECT
    SUM(credit_balance) AS DuNo_NganHan
FROM LastRow
WHERE rn = 1;

WITH LastRow AS (
    SELECT
        account_no,
        credit_balance,
        ROW_NUMBER() OVER (
            PARTITION BY account_no
            ORDER BY Posting_Date DESC, ID DESC
        ) AS rn
    FROM FACT_CASHFLOW
    WHERE account_no = '34112'
)

SELECT
    SUM(credit_balance) AS DuNo_DaiHan
FROM LastRow
WHERE rn = 1;