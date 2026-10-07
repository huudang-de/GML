-- TONG HOP SQL TEST SCRIPT (SIT)
-- DU AN GO MINH LONG

-- Bảng: dim_account

-- TEST SCRIPT: sit_dim_account_duplicate
SELECT account_no, COUNT(*) FROM silver.dim_account GROUP BY account_no HAVING COUNT(*) > 1;

-- TEST SCRIPT: sit_dim_account_rowcount
SELECT COUNT(*) AS total_rows FROM silver.dim_account;

-- Bảng: dim_accountnumber

-- TEST SCRIPT: sit_dim_accountnumber_duplicate
SELECT account_bank, COUNT(*) FROM silver.dim_accountnumber GROUP BY account_bank HAVING COUNT(*) > 1;

-- TEST SCRIPT: sit_dim_accountnumber_rowcount
SELECT COUNT(*) AS total_rows FROM silver.dim_accountnumber;

-- Bảng: dim_bank

-- TEST SCRIPT: sit_dim_bank_duplicate
SELECT bank_code, COUNT(*) FROM silver.dim_bank GROUP BY bank_code HAVING COUNT(*) > 1;

-- TEST SCRIPT: sit_dim_bank_rowcount
SELECT COUNT(*) AS total_rows FROM silver.dim_bank;

-- Bảng: dim_partner

-- TEST SCRIPT: sit_dim_partner_duplicate
SELECT partner_code, COUNT(*) FROM silver.dim_partner GROUP BY partner_code HAVING COUNT(*) > 1;

-- TEST SCRIPT: sit_dim_partner_rowcount
SELECT COUNT(*) AS total_rows FROM silver.dim_partner;

-- Bảng: dim_product

-- TEST SCRIPT: sit_dim_product_duplicate
SELECT product_code, COUNT(*) FROM silver.dim_product GROUP BY product_code HAVING COUNT(*) > 1;

-- TEST SCRIPT: sit_dim_product_rowcount
SELECT COUNT(*) AS total_rows FROM silver.dim_product;

-- Bảng: dim_reportitem

-- TEST SCRIPT: sit_dim_reportitem_duplicate
SELECT item_code, COUNT(*) FROM silver.dim_reportitem GROUP BY item_code HAVING COUNT(*) > 1;

-- TEST SCRIPT: sit_dim_reportitem_rowcount
SELECT COUNT(*) AS total_rows FROM silver.dim_reportitem;

-- Bảng: dim_warehouse

-- TEST SCRIPT: sit_dim_warehouse_duplicate
SELECT warehouse_code, COUNT(*) FROM silver.dim_warehouse GROUP BY warehouse_code HAVING COUNT(*) > 1;

-- TEST SCRIPT: sit_dim_warehouse_rowcount
SELECT COUNT(*) AS total_rows FROM silver.dim_warehouse;

-- Bảng: fact_accountspayable

-- TEST SCRIPT: sit_fact_accountspayable_duplicate
SELECT _id, COUNT(*) FROM silver.fact_accountspayable GROUP BY _id HAVING COUNT(*) > 1;

-- TEST SCRIPT: sit_fact_accountspayable_rowcount
SELECT COUNT(*) AS total_rows FROM silver.fact_accountspayable;

-- Bảng: fact_accountsreceivable

-- TEST SCRIPT: sit_fact_accountsreceivable_duplicate
SELECT _id, COUNT(*) FROM silver.fact_accountsreceivable GROUP BY _id HAVING COUNT(*) > 1;

-- TEST SCRIPT: sit_fact_accountsreceivable_rowcount
SELECT COUNT(*) AS total_rows FROM silver.fact_accountsreceivable;

-- Bảng: fact_balancesheet

-- TEST SCRIPT: sit_fact_balancesheet_duplicate
SELECT reporting_date, indicator_code, COUNT(*) FROM silver.fact_balancesheet GROUP BY reporting_date, indicator_code HAVING COUNT(*) > 1;

-- TEST SCRIPT: sit_fact_balancesheet_rowcount
SELECT COUNT(*) AS total_rows FROM silver.fact_balancesheet;

-- Bảng: fact_businessplan

-- TEST SCRIPT: sit_fact_businessplan_duplicate
SELECT indicator_code, month, COUNT(*) FROM silver.fact_businessplan GROUP BY indicator_code, month HAVING COUNT(*) > 1;

-- TEST SCRIPT: sit_fact_businessplan_rowcount
SELECT COUNT(*) AS total_rows FROM silver.fact_businessplan;

-- Bảng: fact_cashflow

-- TEST SCRIPT: sit_fact_cashflow_duplicate
SELECT _id, COUNT(*) FROM silver.fact_cashflow GROUP BY _id HAVING COUNT(*) > 1;

-- TEST SCRIPT: sit_fact_cashflow_rowcount
SELECT COUNT(*) AS total_rows FROM silver.fact_cashflow;

-- Bảng: fact_collateral

-- TEST SCRIPT: sit_fact_collateral_duplicate
SELECT row_id, COUNT(*) FROM silver.fact_collateral GROUP BY row_id HAVING COUNT(*) > 1;

-- TEST SCRIPT: sit_fact_collateral_rowcount
SELECT COUNT(*) AS total_rows FROM silver.fact_collateral;

-- Bảng: fact_creditlimitsummary

-- TEST SCRIPT: sit_fact_creditlimitsummary_duplicate
SELECT bank_code, COUNT(*) FROM silver.fact_creditlimitsummary GROUP BY bank_code HAVING COUNT(*) > 1;

-- TEST SCRIPT: sit_fact_creditlimitsummary_rowcount
SELECT COUNT(*) AS total_rows FROM silver.fact_creditlimitsummary;

-- Bảng: fact_incomestatement

-- TEST SCRIPT: sit_fact_incomestatement_duplicate
SELECT indicator_code, month, COUNT(*) FROM silver.fact_incomestatement GROUP BY indicator_code, month HAVING COUNT(*) > 1;

-- TEST SCRIPT: sit_fact_incomestatement_rowcount
SELECT COUNT(*) AS total_rows FROM silver.fact_incomestatement;

-- Bảng: fact_inventory_balance

-- TEST SCRIPT: sit_fact_inventory_balance_duplicate
SELECT snapshot_date, product_code, warehouse_code, COUNT(*) FROM silver.fact_inventory_balance GROUP BY snapshot_date, product_code, warehouse_code HAVING COUNT(*) > 1;

-- TEST SCRIPT: sit_fact_inventory_balance_rowcount
SELECT COUNT(*) AS total_rows FROM silver.fact_inventory_balance;

-- Bảng: fact_inventoryinward

-- TEST SCRIPT: sit_fact_inventoryinward_duplicate
SELECT _id, COUNT(*) FROM silver.fact_inventoryinward GROUP BY _id HAVING COUNT(*) > 1;

-- TEST SCRIPT: sit_fact_inventoryinward_rowcount
SELECT COUNT(*) AS total_rows FROM silver.fact_inventoryinward;

-- Bảng: fact_inventoryoutward

-- TEST SCRIPT: sit_fact_inventoryoutward_duplicate
SELECT _id, COUNT(*) FROM silver.fact_inventoryoutward GROUP BY _id HAVING COUNT(*) > 1;

-- TEST SCRIPT: sit_fact_inventoryoutward_rowcount
SELECT COUNT(*) AS total_rows FROM silver.fact_inventoryoutward;

-- Bảng: fact_loan

-- TEST SCRIPT: sit_fact_loan_duplicate
SELECT contract_no, COUNT(*) FROM silver.fact_loan GROUP BY contract_no HAVING COUNT(*) > 1;

-- TEST SCRIPT: sit_fact_loan_rowcount
SELECT COUNT(*) AS total_rows FROM silver.fact_loan;

-- Bảng: fact_termdeposit

-- TEST SCRIPT: sit_fact_termdeposit_duplicate
SELECT _id, COUNT(*) FROM silver.fact_termdeposit GROUP BY _id HAVING COUNT(*) > 1;

-- TEST SCRIPT: sit_fact_termdeposit_rowcount
SELECT COUNT(*) AS total_rows FROM silver.fact_termdeposit;

