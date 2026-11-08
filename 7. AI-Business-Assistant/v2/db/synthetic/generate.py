"""Deterministic 12-Month Synthetic Warehouse Generator.

Specification:
- Spec §3.1, §6.1, §6 Warning
- Plan Task 1 (T1-synth)
- Generates 7 dim_* and 13 fact_* tables in 'synthetic' schema on gml_synth.
- Deterministic data covering 12 months (2025-08-31 to 2026-07-31).
- 5 labeled anomalies embedded for automated verification.
- Applies ai_views on top of synthetic schema via apply_all.
- Produces deterministic EV-03 checksum file (v2/db/synthetic/CHECKSUM.txt).
"""

import argparse
from datetime import date, datetime
import hashlib
from pathlib import Path
import random
import sys

# Ensure v2 package root is in sys.path
V2_DIR = Path(__file__).resolve().parent.parent.parent
if str(V2_DIR) not in sys.path:
    sys.path.insert(0, str(V2_DIR))

import sqlalchemy as sa
from sqlalchemy.engine import Engine

from app.core.config import Settings
from db.apply_db import apply_all, ensure_database_exists, get_admin_engine
from db.synthetic.report_items_data import REPORT_ITEMS

SYNTHETIC_DIR = Path(__file__).resolve().parent
DEFAULT_CHECKSUM_PATH = SYNTHETIC_DIR / "CHECKSUM.txt"
ENV_PATH = V2_DIR / ".env"

ALL_TABLES = [
    # 7 Dim tables
    "dim_bank",
    "dim_account",
    "dim_accountnumber",
    "dim_reportitem",
    "dim_product",
    "dim_warehouse",
    "dim_partner",
    # 13 Fact tables
    "fact_creditlimitsummary",
    "fact_collateral",
    "fact_loan",
    "fact_cashflow",
    "fact_balancesheet",
    "fact_incomestatement",
    "fact_inventory_balance",
    "fact_inventoryinward",
    "fact_inventoryoutward",
    "fact_accountsreceivable",
    "fact_accountspayable",
    "fact_termdeposit",
    "fact_businessplan",
]

MONTH_ENDS = [
    date(2025, 8, 31),
    date(2025, 9, 30),
    date(2025, 10, 31),
    date(2025, 11, 30),  # ANOM-03
    date(2025, 12, 31),
    date(2026, 1, 31),   # ANOM-01 baseline
    date(2026, 2, 28),   # ANOM-05
    date(2026, 3, 31),   # ANOM-02
    date(2026, 4, 30),
    date(2026, 5, 31),
    date(2026, 6, 30),   # ANOM-01 prior month
    date(2026, 7, 31),   # Cut-off date, ANOM-01, ANOM-04
]


def _get_settings() -> Settings:
    if ENV_PATH.exists():
        return Settings(_env_file=str(ENV_PATH))
    return Settings()


def create_synthetic_schema_and_tables(engine: Engine) -> None:
    """Create schema 'synthetic' and all 20 required tables."""
    ddl_statements = [
        "CREATE SCHEMA IF NOT EXISTS synthetic;",
        # 1. dim_bank
        """
        CREATE TABLE IF NOT EXISTS synthetic.dim_bank (
            _id BIGINT PRIMARY KEY,
            bank_code VARCHAR,
            bank_name VARCHAR,
            code1 VARCHAR,
            code2 VARCHAR,
            _source_file VARCHAR,
            _loaded_at TIMESTAMP,
            _batch_id VARCHAR
        );
        """,
        # 2. dim_account
        """
        CREATE TABLE IF NOT EXISTS synthetic.dim_account (
            _id BIGINT PRIMARY KEY,
            account_no VARCHAR,
            account_name VARCHAR,
            account_bank VARCHAR,
            _source_file VARCHAR,
            _loaded_at TIMESTAMP,
            _batch_id VARCHAR
        );
        """,
        # 3. dim_accountnumber
        """
        CREATE TABLE IF NOT EXISTS synthetic.dim_accountnumber (
            _id BIGINT PRIMARY KEY,
            account_bank VARCHAR,
            bank_name VARCHAR,
            bank_code VARCHAR,
            _source_file VARCHAR,
            _loaded_at TIMESTAMP,
            _batch_id VARCHAR
        );
        """,
        # 4. dim_reportitem
        """
        CREATE TABLE IF NOT EXISTS synthetic.dim_reportitem (
            _id BIGINT PRIMARY KEY,
            item_id VARCHAR,
            report_type VARCHAR,
            item_code VARCHAR,
            item_name VARCHAR,
            parent_id VARCHAR,
            sort_index INTEGER,
            _source_file VARCHAR,
            _loaded_at TIMESTAMP,
            _batch_id VARCHAR
        );
        """,
        # 5. dim_product
        """
        CREATE TABLE IF NOT EXISTS synthetic.dim_product (
            _id BIGINT PRIMARY KEY,
            product_code VARCHAR,
            product_name TEXT,
            unit_of_measure VARCHAR,
            product_category VARCHAR,
            _source_file VARCHAR,
            _loaded_at TIMESTAMP,
            _batch_id VARCHAR
        );
        """,
        # 6. dim_warehouse
        """
        CREATE TABLE IF NOT EXISTS synthetic.dim_warehouse (
            _id BIGINT PRIMARY KEY,
            warehouse_code VARCHAR,
            warehouse_name VARCHAR,
            _source_file VARCHAR,
            _loaded_at TIMESTAMP,
            _batch_id VARCHAR
        );
        """,
        # 7. dim_partner
        """
        CREATE TABLE IF NOT EXISTS synthetic.dim_partner (
            _id BIGINT PRIMARY KEY,
            partner_code VARCHAR,
            partner_name TEXT,
            address TEXT,
            tax VARCHAR,
            partner_group VARCHAR,
            _source_file VARCHAR,
            _loaded_at TIMESTAMP,
            _batch_id VARCHAR
        );
        """,
        # 8. fact_creditlimitsummary
        """
        CREATE TABLE IF NOT EXISTS synthetic.fact_creditlimitsummary (
            _id BIGINT PRIMARY KEY,
            stt VARCHAR,
            bank_code VARCHAR,
            granted_limit NUMERIC,
            principal_balance NUMERIC,
            remaining_disbursement NUMERIC,
            id INTEGER,
            credit_limit NUMERIC,
            limit_type VARCHAR,
            interest_rate DOUBLE PRECISION,
            _source_file VARCHAR,
            _loaded_at TIMESTAMP,
            _batch_id VARCHAR
        );
        """,
        # 9. fact_collateral
        """
        CREATE TABLE IF NOT EXISTS synthetic.fact_collateral (
            _id BIGINT PRIMARY KEY,
            collateral_type VARCHAR,
            appraised_value NUMERIC,
            collateral_coefficient VARCHAR,
            loan_value NUMERIC,
            max_loan_amount NUMERIC,
            row_id INTEGER,
            bank_code VARCHAR,
            _source_file VARCHAR,
            _loaded_at TIMESTAMP,
            _batch_id VARCHAR
        );
        """,
        # 10. fact_loan
        """
        CREATE TABLE IF NOT EXISTS synthetic.fact_loan (
            _id BIGINT PRIMARY KEY,
            bank_code VARCHAR,
            contract_no VARCHAR,
            total_credit_limit NUMERIC,
            remaining_principal NUMERIC,
            interest_rate DOUBLE PRECISION,
            disbursement_date DATE,
            maturity_date DATE,
            principal_payment_amount NUMERIC,
            id INTEGER,
            _source_file VARCHAR,
            _loaded_at TIMESTAMP,
            _batch_id VARCHAR
        );
        """,
        # 11. fact_cashflow
        """
        CREATE TABLE IF NOT EXISTS synthetic.fact_cashflow (
            _id BIGINT PRIMARY KEY,
            posting_date DATE,
            voucher_date DATE,
            voucher_no VARCHAR,
            description VARCHAR,
            reciprocal_account VARCHAR,
            partner_code VARCHAR,
            debit_amount NUMERIC,
            credit_amount NUMERIC,
            debit_balance NUMERIC,
            credit_balance NUMERIC,
            id INTEGER,
            account_no VARCHAR,
            _source_file VARCHAR,
            _loaded_at TIMESTAMP,
            _batch_id VARCHAR
        );
        """,
        # 12. fact_balancesheet
        """
        CREATE TABLE IF NOT EXISTS synthetic.fact_balancesheet (
            _id BIGINT PRIMARY KEY,
            indicator_code VARCHAR,
            ending_balance NUMERIC,
            beginning_balance NUMERIC,
            reporting_date DATE,
            _source_file VARCHAR,
            _loaded_at TIMESTAMP,
            _batch_id VARCHAR
        );
        """,
        # 13. fact_incomestatement
        """
        CREATE TABLE IF NOT EXISTS synthetic.fact_incomestatement (
            _id BIGINT PRIMARY KEY,
            indicator_code VARCHAR,
            indicator_name VARCHAR,
            current_period_amount NUMERIC,
            previous_period_amount NUMERIC,
            month DATE,
            _source_file VARCHAR,
            _loaded_at TIMESTAMP,
            _batch_id VARCHAR
        );
        """,
        # 14. fact_inventory_balance
        """
        CREATE TABLE IF NOT EXISTS synthetic.fact_inventory_balance (
            _id BIGINT PRIMARY KEY,
            warehouse_code VARCHAR,
            product_code VARCHAR,
            ending_quantity DOUBLE PRECISION,
            ending_value NUMERIC,
            id INTEGER,
            snapshot_date DATE,
            _source_file VARCHAR,
            _loaded_at TIMESTAMP,
            _batch_id VARCHAR
        );
        """,
        # 15. fact_inventoryinward
        """
        CREATE TABLE IF NOT EXISTS synthetic.fact_inventoryinward (
            _id BIGINT PRIMARY KEY,
            posting_date DATE,
            voucher_no VARCHAR,
            invoice_no VARCHAR,
            invoice_date DATE,
            warehouse_code VARCHAR,
            product_code VARCHAR,
            partner_code VARCHAR,
            currency VARCHAR,
            exchange_rate DOUBLE PRECISION,
            inward_quantity DOUBLE PRECISION,
            inward_value NUMERIC,
            id INTEGER,
            _source_file VARCHAR,
            _loaded_at TIMESTAMP,
            _batch_id VARCHAR
        );
        """,
        # 16. fact_inventoryoutward
        """
        CREATE TABLE IF NOT EXISTS synthetic.fact_inventoryoutward (
            _id BIGINT PRIMARY KEY,
            posting_date DATE,
            voucher_no VARCHAR,
            invoice_no VARCHAR,
            invoice_date DATE,
            warehouse_code VARCHAR,
            product_code VARCHAR,
            partner_code VARCHAR,
            currency VARCHAR,
            exchange_rate DOUBLE PRECISION,
            outward_quantity DOUBLE PRECISION,
            outward_value DOUBLE PRECISION,
            id INTEGER,
            _source_file VARCHAR,
            _loaded_at TIMESTAMP,
            _batch_id VARCHAR
        );
        """,
        # 17. fact_accountsreceivable
        """
        CREATE TABLE IF NOT EXISTS synthetic.fact_accountsreceivable (
            _id BIGINT PRIMARY KEY,
            posting_date DATE,
            voucher_no VARCHAR,
            invoice_no VARCHAR,
            invoice_date DATE,
            description VARCHAR,
            partner_code VARCHAR,
            reciprocal_account VARCHAR,
            debit_amount NUMERIC,
            credit_amount NUMERIC,
            ending_debit_balance NUMERIC,
            ending_credit_balance NUMERIC,
            currency VARCHAR,
            exchange_rate NUMERIC,
            id INTEGER,
            _source_file VARCHAR,
            _loaded_at TIMESTAMP,
            _batch_id VARCHAR
        );
        """,
        # 18. fact_accountspayable
        """
        CREATE TABLE IF NOT EXISTS synthetic.fact_accountspayable (
            _id BIGINT PRIMARY KEY,
            partner_code VARCHAR,
            posting_date DATE,
            voucher_no VARCHAR,
            invoice_no VARCHAR,
            invoice_date DATE,
            description TEXT,
            reciprocal_account VARCHAR,
            currency VARCHAR,
            exchange_rate NUMERIC,
            debit_amount NUMERIC,
            credit_amount NUMERIC,
            ending_debit_balance NUMERIC,
            ending_credit_balance NUMERIC,
            id INTEGER,
            _source_file VARCHAR,
            _loaded_at TIMESTAMP,
            _batch_id VARCHAR
        );
        """,
        # 19. fact_termdeposit
        """
        CREATE TABLE IF NOT EXISTS synthetic.fact_termdeposit (
            _id BIGINT PRIMARY KEY,
            stt INTEGER,
            passbook_no VARCHAR,
            bank_code VARCHAR,
            interest_rate DOUBLE PRECISION,
            term INTEGER,
            original_amount NUMERIC,
            remaining_value NUMERIC,
            deposit_date DATE,
            maturity_date DATE,
            settlement_date DATE,
            id INTEGER,
            _source_file VARCHAR,
            _loaded_at TIMESTAMP,
            _batch_id VARCHAR
        );
        """,
        # 20. fact_businessplan
        """
        CREATE TABLE IF NOT EXISTS synthetic.fact_businessplan (
            _id BIGINT PRIMARY KEY,
            indicator_code VARCHAR,
            month DATE,
            target_amount NUMERIC,
            _source_file VARCHAR,
            _loaded_at TIMESTAMP,
            _batch_id VARCHAR
        );
        """,
    ]

    with engine.connect() as conn:
        for stmt in ddl_statements:
            conn.execute(sa.text(stmt))
        conn.commit()


def populate_synthetic_data(engine: Engine, seed: int = 42) -> None:
    """Insert deterministic records covering 12 months with 5 labeled anomalies."""
    rng = random.Random(seed)
    fixed_loaded_at = datetime(2026, 7, 31, 0, 0, 0)
    source_file = "SYNTHETIC_GENERATOR"
    batch_id = f"BATCH_SYNTH_{seed}"

    # Truncate all tables first to guarantee idempotent generation
    with engine.connect() as conn:
        for t in reversed(ALL_TABLES):
            conn.execute(sa.text(f"TRUNCATE TABLE synthetic.{t} RESTART IDENTITY CASCADE;"))
        conn.commit()

    # -------------------------------------------------------------------------
    # 1. dim_bank (7 rows)
    # -------------------------------------------------------------------------
    banks_data = [
        (1, "SYNTH_VCB", "Ngân hàng Ngoại thương Việt Nam (Vietcombank)", "VCB", "VIETCOMBANK"),
        (2, "SYNTH_BIDV", "Ngân hàng Đầu tư và Phát triển Việt Nam (BIDV)", "BIDV", "BIDV"),
        (3, "SYNTH_TCB", "Ngân hàng Kỹ thương Việt Nam (Techcombank)", "TCB", "TECHCOMBANK"),
        (4, "SYNTH_CTG", "Ngân hàng Công thương Việt Nam (VietinBank)", "CTG", "VIETINBANK"),
        (5, "SYNTH_MBB", "Ngân hàng Quân đội (MBBank)", "MBB", "MBBANK"),
    ]
    with engine.connect() as conn:
        for r in banks_data:
            conn.execute(
                sa.text("""
                    INSERT INTO synthetic.dim_bank (_id, bank_code, bank_name, code1, code2, _source_file, _loaded_at, _batch_id)
                    VALUES (:id, :code, :name, :c1, :c2, :src, :lat, :bid)
                """),
                {"id": r[0], "code": r[1], "name": r[2], "c1": r[3], "c2": r[4], "src": source_file, "lat": fixed_loaded_at, "bid": batch_id},
            )
        conn.commit()

    # -------------------------------------------------------------------------
    # 2. dim_account
    # -------------------------------------------------------------------------
    accounts_data = [
        (1, "1111", "Tiền mặt VND", None),
        (2, "1121", "Tiền gửi ngân hàng VND", "SYNTH_ACC_112101"),
        (3, "1122", "Tiền gửi ngân hàng ngoại tệ", "SYNTH_ACC_112201"),
        (4, "131", "Phải thu của khách hàng", None),
        (5, "331", "Phải trả cho người bán", None),
        (6, "34111", "Vay ngắn hạn ngân hàng", None),
        (7, "34112", "Vay dài hạn ngân hàng", None),
        (8, "34113", "Vay ngắn hạn tổ chức khác", None),
        (9, "34114", "Vay ngắn hạn cá nhân", None),
        (10, "5111", "Doanh thu bán hàng hóa", None),
        (11, "515", "Doanh thu hoạt động tài chính", None),
        (12, "632", "Giá vốn hàng bán", None),
        (13, "635", "Chi phí tài chính", None),
    ]
    with engine.connect() as conn:
        for r in accounts_data:
            conn.execute(
                sa.text("""
                    INSERT INTO synthetic.dim_account (_id, account_no, account_name, account_bank, _source_file, _loaded_at, _batch_id)
                    VALUES (:id, :no, :name, :ab, :src, :lat, :bid)
                """),
                {"id": r[0], "no": r[1], "name": r[2], "ab": r[3], "src": source_file, "lat": fixed_loaded_at, "bid": batch_id},
            )
        conn.commit()

    # -------------------------------------------------------------------------
    # 3. dim_accountnumber
    # -------------------------------------------------------------------------
    accountnumbers_data = [
        (1, "SYNTH_ACC_112101", "Vietcombank Thăng Long", "SYNTH_VCB"),
        (2, "SYNTH_ACC_112201", "Techcombank Hội Sở", "SYNTH_TCB"),
    ]
    with engine.connect() as conn:
        for r in accountnumbers_data:
            conn.execute(
                sa.text("""
                    INSERT INTO synthetic.dim_accountnumber (_id, account_bank, bank_name, bank_code, _source_file, _loaded_at, _batch_id)
                    VALUES (:id, :ab, :bname, :bcode, :src, :lat, :bid)
                """),
                {"id": r[0], "ab": r[1], "bname": r[2], "bcode": r[3], "src": source_file, "lat": fixed_loaded_at, "bid": batch_id},
            )
        conn.commit()

    # -------------------------------------------------------------------------
    # 4. dim_reportitem (147 standard items from REPORT_ITEMS)
    # -------------------------------------------------------------------------
    with engine.connect() as conn:
        for idx, item in enumerate(REPORT_ITEMS, start=1):
            conn.execute(
                sa.text("""
                    INSERT INTO synthetic.dim_reportitem (_id, item_id, report_type, item_code, item_name, parent_id, sort_index, _source_file, _loaded_at, _batch_id)
                    VALUES (:id, :iid, :rtype, :icode, :iname, :pid, :sort, :src, :lat, :bid)
                """),
                {
                    "id": idx,
                    "iid": item[0],
                    "rtype": item[1],
                    "icode": item[2],
                    "iname": item[3],
                    "pid": item[4],
                    "sort": item[5],
                    "src": source_file,
                    "lat": fixed_loaded_at,
                    "bid": batch_id,
                },
            )
        conn.commit()

    # -------------------------------------------------------------------------
    # 5. dim_product
    # -------------------------------------------------------------------------
    products_data = [
        (1, "SYNTH_SKU_MDF17", "Ván MDF 17mm chống ẩm", "Tấm", "Ván MDF"),
        (2, "SYNTH_SKU_MFC18", "Ván MFC 18mm tiêu chuẩn", "Tấm", "Ván MFC"),
        (3, "SYNTH_SKU_PLY12", "Ván Plywood 12mm phủ phim", "Tấm", "Ván Plywood"),
        (4, "SYNTH_SKU_LAM08", "Gỗ Laminate cao cấp 0.8mm", "Tấm", "Laminate"),
        (5, "SYNTH_SKU_VENEER", "Veneer sồi tự nhiên 0.6mm", "m2", "Veneer"),
    ]
    with engine.connect() as conn:
        for r in products_data:
            conn.execute(
                sa.text("""
                    INSERT INTO synthetic.dim_product (_id, product_code, product_name, unit_of_measure, product_category, _source_file, _loaded_at, _batch_id)
                    VALUES (:id, :pcode, :pname, :uom, :cat, :src, :lat, :bid)
                """),
                {"id": r[0], "pcode": r[1], "pname": r[2], "uom": r[3], "cat": r[4], "src": source_file, "lat": fixed_loaded_at, "bid": batch_id},
            )
        conn.commit()

    # -------------------------------------------------------------------------
    # 6. dim_warehouse
    # -------------------------------------------------------------------------
    warehouses_data = [
        (1, "SYNTH_KHO_01", "Kho Tổng Bình Dương"),
        (2, "SYNTH_KHO_02", "Kho Nguyên Liệu Hà Nội"),
        (3, "SYNTH_KHO_03", "Kho Thành Phẩm Đà Nẵng"),
    ]
    with engine.connect() as conn:
        for r in warehouses_data:
            conn.execute(
                sa.text("""
                    INSERT INTO synthetic.dim_warehouse (_id, warehouse_code, warehouse_name, _source_file, _loaded_at, _batch_id)
                    VALUES (:id, :wcode, :wname, :src, :lat, :bid)
                """),
                {"id": r[0], "wcode": r[1], "wname": r[2], "src": source_file, "lat": fixed_loaded_at, "bid": batch_id},
            )
        conn.commit()

    # -------------------------------------------------------------------------
    # 7. dim_partner
    # -------------------------------------------------------------------------
    partners_data = [
        (1, "SYNTH_CUST_001", "Công ty TNHH Nội thất An Cường", "Bình Dương", "0301112223", "Khách hàng"),
        (2, "SYNTH_CUST_002", "Công ty CP Kiến trúc Hoàng Gia", "Hà Nội", "0102223334", "Khách hàng"),
        (3, "SYNTH_SUPP_001", "Công ty CP Hóa chất Keo Dán Đức Mỹ", "Đồng Nai", "3603334445", "Nhà cung cấp"),
        (4, "SYNTH_SUPP_002", "Tập đoàn Lâm nghiệp Siam Wood", "Thái Lan", "TAX_SIAM_01", "Nhà cung cấp"),
        (5, "SYNTH_BOTH_001", "Công ty CP Sản xuất và Thương mại Việt Á", "TP.HCM", "0304445556", "Khách hàng/ nhà cung cấp"),
    ]
    with engine.connect() as conn:
        for r in partners_data:
            conn.execute(
                sa.text("""
                    INSERT INTO synthetic.dim_partner (_id, partner_code, partner_name, address, tax, partner_group, _source_file, _loaded_at, _batch_id)
                    VALUES (:id, :pcode, :pname, :addr, :tax, :grp, :src, :lat, :bid)
                """),
                {"id": r[0], "pcode": r[1], "pname": r[2], "addr": r[3], "tax": r[4], "grp": r[5], "src": source_file, "lat": fixed_loaded_at, "bid": batch_id},
            )
        conn.commit()

    # -------------------------------------------------------------------------
    # 8. fact_creditlimitsummary (ANOM-04: ratio = 0.80023729)
    # -------------------------------------------------------------------------
    # Total granted_limit = 295,000,000,000
    # Total principal_balance = 236,070,000,000
    # Total remaining = 58,930,000,000
    credit_limits = [
        (1, "1", "SYNTH_VCB", 150000000000.0, 120070000000.0, 29930000000.0, 1, 200000000000.0, "Hạn mức ngắn hạn", 0.055),
        (2, "2", "SYNTH_BIDV", 100000000000.0, 80000000000.0, 20000000000.0, 2, 150000000000.0, "Hạn mức ngắn hạn", 0.058),
        (3, "3", "SYNTH_TCB", 45000000000.0, 36000000000.0, 9000000000.0, 3, 100000000000.0, "Hạn mức ngắn hạn", 0.062),
    ]
    with engine.connect() as conn:
        for r in credit_limits:
            conn.execute(
                sa.text("""
                    INSERT INTO synthetic.fact_creditlimitsummary (
                        _id, stt, bank_code, granted_limit, principal_balance, remaining_disbursement,
                        id, credit_limit, limit_type, interest_rate, _source_file, _loaded_at, _batch_id
                    ) VALUES (:id, :stt, :bcode, :glimit, :pbal, :rdisb, :fid, :clim, :ltype, :irate, :src, :lat, :bid)
                """),
                {
                    "id": r[0], "stt": r[1], "bcode": r[2], "glimit": r[3], "pbal": r[4], "rdisb": r[5],
                    "fid": r[6], "clim": r[7], "ltype": r[8], "irate": r[9], "src": source_file, "lat": fixed_loaded_at, "bid": batch_id,
                },
            )
        conn.commit()

    # -------------------------------------------------------------------------
    # 9. fact_collateral
    # -------------------------------------------------------------------------
    collaterals = [
        (1, "Bất động sản nhà xưởng", 250000000000.0, "70%", 175000000000.0, 175000000000.0, 1, "SYNTH_VCB"),
        (2, "Dây chuyền máy móc chế biến gỗ", 150000000000.0, "65%", 97500000000.0, 97500000000.0, 2, "SYNTH_BIDV"),
        (3, "Kho bãi và quyền sử dụng đất", 100000000000.0, "70%", 70000000000.0, 70000000000.0, 3, "SYNTH_TCB"),
    ]
    with engine.connect() as conn:
        for r in collaterals:
            conn.execute(
                sa.text("""
                    INSERT INTO synthetic.fact_collateral (
                        _id, collateral_type, appraised_value, collateral_coefficient, loan_value,
                        max_loan_amount, row_id, bank_code, _source_file, _loaded_at, _batch_id
                    ) VALUES (:id, :ctype, :aval, :coeff, :lval, :mloan, :rid, :bcode, :src, :lat, :bid)
                """),
                {
                    "id": r[0], "ctype": r[1], "aval": r[2], "coeff": r[3], "lval": r[4],
                    "mloan": r[5], "rid": r[6], "bcode": r[7], "src": source_file, "lat": fixed_loaded_at, "bid": batch_id,
                },
            )
        conn.commit()

    # -------------------------------------------------------------------------
    # 10. fact_loan
    # -------------------------------------------------------------------------
    loans = [
        (1, "SYNTH_VCB", "SYNTH_HD_VCB_01", 100000000000.0, 80000000000.0, 0.055, date(2025, 9, 15), date(2026, 9, 15), 5000000000.0, 1),
        (2, "SYNTH_BIDV", "SYNTH_HD_BIDV_01", 80000000000.0, 60000000000.0, 0.058, date(2025, 10, 20), date(2026, 10, 20), 4000000000.0, 2),
    ]
    with engine.connect() as conn:
        for r in loans:
            conn.execute(
                sa.text("""
                    INSERT INTO synthetic.fact_loan (
                        _id, bank_code, contract_no, total_credit_limit, remaining_principal, interest_rate,
                        disbursement_date, maturity_date, principal_payment_amount, id, _source_file, _loaded_at, _batch_id
                    ) VALUES (:id, :bcode, :cno, :clim, :rprin, :irate, :ddate, :mdate, :ppay, :fid, :src, :lat, :bid)
                """),
                {
                    "id": r[0], "bcode": r[1], "cno": r[2], "clim": r[3], "rprin": r[4], "irate": r[5],
                    "ddate": r[6], "mdate": r[7], "ppay": r[8], "fid": r[9], "src": source_file, "lat": fixed_loaded_at, "bid": batch_id,
                },
            )
        conn.commit()

    # -------------------------------------------------------------------------
    # 11. fact_cashflow (ANOM-01 and ANOM-05)
    # -------------------------------------------------------------------------
    cashflows: list[dict] = []
    cf_id = 1

    # ANOM-01: Historical credit balances on account 34111 across 12 months
    # 2026-01: 314,700,000,000 (Exact baseline)
    # 2026-06: 283,700,000,000 (Exact prior)
    # 2026-07: 236,070,000,000 (Exact cut-off -> MoM = -0.1678886...)
    monthly_debt = {
        date(2025, 8, 31): 300000000000.0,
        date(2025, 9, 30): 305000000000.0,
        date(2025, 10, 31): 310000000000.0,
        date(2025, 11, 30): 312000000000.0,
        date(2025, 12, 31): 314000000000.0,
        date(2026, 1, 31): 314700000000.0,
        date(2026, 2, 28): 310000000000.0,
        date(2026, 3, 31): 305000000000.0,
        date(2026, 4, 30): 298000000000.0,
        date(2026, 5, 31): 290000000000.0,
        date(2026, 6, 30): 283700000000.0,
        date(2026, 7, 31): 236070000000.0,
    }

    for dt, debt_val in monthly_debt.items():
        ym_str = dt.strftime("%Y%m")
        cashflows.append({
            "_id": cf_id,
            "posting_date": dt,
            "voucher_date": dt,
            "voucher_no": f"SYNTH_PKT_{ym_str}_01",
            "description": f"Chốt sổ dư nợ vay ngắn hạn tháng {dt.strftime('%m/%Y')}",
            "reciprocal_account": None,
            "partner_code": "SYNTH_SUPP_001",
            "debit_amount": 0.0,
            "credit_amount": 0.0,
            "debit_balance": 0.0,
            "credit_balance": debt_val,
            "id": cf_id,
            "account_no": "34111",
            "_source_file": source_file,
            "_loaded_at": fixed_loaded_at,
            "_batch_id": batch_id,
        })
        cf_id += 1

    # ANOM-05: External cashflow in 2026-02 net = -45,000,000,000
    # Debit = 5B, Credit = 50B
    cashflows.append({
        "_id": cf_id,
        "posting_date": date(2026, 2, 15),
        "voucher_date": date(2026, 2, 15),
        "voucher_no": "SYNTH_UNC_20260215_01",
        "description": "Thanh toán công nợ mua nguyên vật liệu sau Tết",
        "reciprocal_account": "331",
        "partner_code": "SYNTH_SUPP_001",
        "debit_amount": 0.0,
        "credit_amount": 50000000000.0,
        "debit_balance": 0.0,
        "credit_balance": 50000000000.0,
        "id": cf_id,
        "account_no": "1121",
        "_source_file": source_file,
        "_loaded_at": fixed_loaded_at,
        "_batch_id": batch_id,
    })
    cf_id += 1

    cashflows.append({
        "_id": cf_id,
        "posting_date": date(2026, 2, 20),
        "voucher_date": date(2026, 2, 20),
        "voucher_no": "SYNTH_GBN_20260220_01",
        "description": "Khách hàng thanh toán tiền hàng đợt 1",
        "reciprocal_account": "131",
        "partner_code": "SYNTH_CUST_001",
        "debit_amount": 5000000000.0,
        "credit_amount": 0.0,
        "debit_balance": 5000000000.0,
        "credit_balance": 0.0,
        "id": cf_id,
        "account_no": "1121",
        "_source_file": source_file,
        "_loaded_at": fixed_loaded_at,
        "_batch_id": batch_id,
    })
    cf_id += 1

    # Routine monthly external cashflow for the other 11 months (positive net ~5B)
    for m_dt in MONTH_ENDS:
        if m_dt.strftime("%Y-%m") == "2026-02":
            continue
        ym_str = m_dt.strftime("%Y%m")
        # Inflow
        cashflows.append({
            "_id": cf_id,
            "posting_date": date(m_dt.year, m_dt.month, 10),
            "voucher_date": date(m_dt.year, m_dt.month, 10),
            "voucher_no": f"SYNTH_GBN_{ym_str}_01",
            "description": f"Thu tiền khách hàng tháng {m_dt.strftime('%m/%Y')}",
            "reciprocal_account": "131",
            "partner_code": "SYNTH_CUST_001",
            "debit_amount": 35000000000.0,
            "credit_amount": 0.0,
            "debit_balance": 35000000000.0,
            "credit_balance": 0.0,
            "id": cf_id,
            "account_no": "1121",
            "_source_file": source_file,
            "_loaded_at": fixed_loaded_at,
            "_batch_id": batch_id,
        })
        cf_id += 1
        # Outflow
        cashflows.append({
            "_id": cf_id,
            "posting_date": date(m_dt.year, m_dt.month, 25),
            "voucher_date": date(m_dt.year, m_dt.month, 25),
            "voucher_no": f"SYNTH_UNC_{ym_str}_02",
            "description": f"Chi trả nhà cung cấp tháng {m_dt.strftime('%m/%Y')}",
            "reciprocal_account": "331",
            "partner_code": "SYNTH_SUPP_001",
            "debit_amount": 0.0,
            "credit_amount": 30000000000.0,
            "debit_balance": 0.0,
            "credit_balance": 30000000000.0,
            "id": cf_id,
            "account_no": "1121",
            "_source_file": source_file,
            "_loaded_at": fixed_loaded_at,
            "_batch_id": batch_id,
        })
        cf_id += 1

    with engine.connect() as conn:
        for cf in cashflows:
            conn.execute(
                sa.text("""
                    INSERT INTO synthetic.fact_cashflow (
                        _id, posting_date, voucher_date, voucher_no, description, reciprocal_account,
                        partner_code, debit_amount, credit_amount, debit_balance, credit_balance,
                        id, account_no, _source_file, _loaded_at, _batch_id
                    ) VALUES (
                        :_id, :posting_date, :voucher_date, :voucher_no, :description, :reciprocal_account,
                        :partner_code, :debit_amount, :credit_amount, :debit_balance, :credit_balance,
                        :id, :account_no, :_source_file, :_loaded_at, :_batch_id
                    )
                """),
                cf,
            )
        conn.commit()

    # -------------------------------------------------------------------------
    # 12. fact_balancesheet (ANOM-03: current_ratio at 2025-11-30 is 1.08)
    # -------------------------------------------------------------------------
    bs_rows: list[dict] = []
    bs_id = 1
    for m_dt in MONTH_ENDS:
        # ANOM-03: at 2025-11-30, B01-DN_100 = 108B, B01-DN_310 = 100B -> ratio = 1.08
        # other 11 months: B01-DN_100 = 145B, B01-DN_310 = 100B -> ratio = 1.45 (in [1.35, 1.55])
        is_anom3_month = (m_dt == date(2025, 11, 30))
        cur_assets = 108000000000.0 if is_anom3_month else 145000000000.0
        cur_liab = 100000000000.0

        items_for_month = [
            ("B01-DN_100", cur_assets, cur_assets * 0.98),
            ("B01-DN_110", 30000000000.0, 28000000000.0),
            ("B01-DN_130", 45000000000.0, 42000000000.0),
            ("B01-DN_140", 50000000000.0, 48000000000.0),
            ("B01-DN_200", 250000000000.0, 248000000000.0),
            ("B01-DN_300", 150000000000.0, 148000000000.0),
            ("B01-DN_310", cur_liab, cur_liab * 0.95),
            ("B01-DN_321", 80000000000.0, 85000000000.0),
            ("B01-DN_330", 50000000000.0, 52000000000.0),
            ("B01-DN_400", 200000000000.0, 195000000000.0),
            ("B01-DN_440", 350000000000.0, 343000000000.0),
        ]
        for item_code, ending, beg in items_for_month:
            bs_rows.append({
                "_id": bs_id,
                "indicator_code": item_code,
                "ending_balance": ending,
                "beginning_balance": beg,
                "reporting_date": m_dt,
                "_source_file": source_file,
                "_loaded_at": fixed_loaded_at,
                "_batch_id": batch_id,
            })
            bs_id += 1

    with engine.connect() as conn:
        for r in bs_rows:
            conn.execute(
                sa.text("""
                    INSERT INTO synthetic.fact_balancesheet (
                        _id, indicator_code, ending_balance, beginning_balance, reporting_date,
                        _source_file, _loaded_at, _batch_id
                    ) VALUES (:_id, :indicator_code, :ending_balance, :beginning_balance, :reporting_date,
                              :_source_file, :_loaded_at, :_batch_id)
                """),
                r,
            )
        conn.commit()

    # -------------------------------------------------------------------------
    # 13. fact_incomestatement (All 12 months have B02-DN_10 > 0, 11 > 0, 23 > 0)
    # -------------------------------------------------------------------------
    is_rows: list[dict] = []
    is_id = 1
    for m_dt in MONTH_ENDS:
        items_for_month = [
            ("B02-DN_01", "Doanh thu bán hàng và cung cấp dịch vụ", 50000000000.0, 48000000000.0),
            ("B02-DN_02", "Các khoản giảm trừ doanh thu", 0.0, 0.0),
            ("B02-DN_10", "Doanh thu thuần", 50000000000.0, 48000000000.0),
            ("B02-DN_11", "Giá vốn hàng bán", 38000000000.0, 36000000000.0),
            ("B02-DN_20", "Lợi nhuận gộp", 12000000000.0, 12000000000.0),
            ("B02-DN_22", "Doanh thu hoạt động tài chính", 1500000000.0, 1400000000.0),
            ("B02-DN_23", "Chi phí tài chính (lãi vay)", 2200000000.0, 2300000000.0),
            ("B02-DN_25", "Chi phí bán hàng", 2500000000.0, 2400000000.0),
            ("B02-DN_26", "Chi phí quản lý doanh nghiệp", 3000000000.0, 2900000000.0),
            ("B02-DN_30", "Lợi nhuận thuần HĐKD", 5800000000.0, 5800000000.0),
            ("B02-DN_50", "Tổng lợi nhuận trước thuế", 5800000000.0, 5800000000.0),
            ("B02-DN_60", "Lợi nhuận sau thuế TNDN", 4640000000.0, 4640000000.0),
        ]
        for icode, iname, cur_val, prev_val in items_for_month:
            is_rows.append({
                "_id": is_id,
                "indicator_code": icode,
                "indicator_name": iname,
                "current_period_amount": cur_val,
                "previous_period_amount": prev_val,
                "month": m_dt,
                "_source_file": source_file,
                "_loaded_at": fixed_loaded_at,
                "_batch_id": batch_id,
            })
            is_id += 1

    with engine.connect() as conn:
        for r in is_rows:
            conn.execute(
                sa.text("""
                    INSERT INTO synthetic.fact_incomestatement (
                        _id, indicator_code, indicator_name, current_period_amount, previous_period_amount,
                        month, _source_file, _loaded_at, _batch_id
                    ) VALUES (:_id, :indicator_code, :indicator_name, :current_period_amount, :previous_period_amount,
                              :month, :_source_file, :_loaded_at, :_batch_id)
                """),
                r,
            )
        conn.commit()

    # -------------------------------------------------------------------------
    # 14. fact_inventory_balance (ANOM-02: SYNTH_SKU_MDF17 total_value = 18.5B at 2026-03-31)
    # -------------------------------------------------------------------------
    inv_rows: list[dict] = []
    inv_id = 1
    for m_dt in MONTH_ENDS:
        # ANOM-02: SKU SYNTH_SKU_MDF17
        if m_dt == date(2026, 3, 31):
            mdf_val = 18500000000.0
            mdf_qty = 37000.0
        else:
            mdf_val = 5000000000.0
            mdf_qty = 10000.0

        inv_rows.append({
            "_id": inv_id,
            "warehouse_code": "SYNTH_KHO_01",
            "product_code": "SYNTH_SKU_MDF17",
            "ending_quantity": mdf_qty,
            "ending_value": mdf_val,
            "id": inv_id,
            "snapshot_date": m_dt,
            "_source_file": source_file,
            "_loaded_at": fixed_loaded_at,
            "_batch_id": batch_id,
        })
        inv_id += 1

        # Other standard SKUs
        inv_rows.append({
            "_id": inv_id,
            "warehouse_code": "SYNTH_KHO_02",
            "product_code": "SYNTH_SKU_MFC18",
            "ending_quantity": 8000.0,
            "ending_value": 3600000000.0,
            "id": inv_id,
            "snapshot_date": m_dt,
            "_source_file": source_file,
            "_loaded_at": fixed_loaded_at,
            "_batch_id": batch_id,
        })
        inv_id += 1

    with engine.connect() as conn:
        for r in inv_rows:
            conn.execute(
                sa.text("""
                    INSERT INTO synthetic.fact_inventory_balance (
                        _id, warehouse_code, product_code, ending_quantity, ending_value,
                        id, snapshot_date, _source_file, _loaded_at, _batch_id
                    ) VALUES (:_id, :warehouse_code, :product_code, :ending_quantity, :ending_value,
                              :id, :snapshot_date, :_source_file, :_loaded_at, :_batch_id)
                """),
                r,
            )
        conn.commit()

    # -------------------------------------------------------------------------
    # 15. fact_inventoryinward
    # -------------------------------------------------------------------------
    inward_rows: list[dict] = []
    inw_id = 1
    for m_dt in MONTH_ENDS:
        ym_str = m_dt.strftime("%Y%m")
        inward_rows.append({
            "_id": inw_id,
            "posting_date": date(m_dt.year, m_dt.month, 5),
            "voucher_no": f"SYNTH_PNK_{ym_str}_01",
            "invoice_no": f"SYNTH_HD_{ym_str}_01",
            "invoice_date": date(m_dt.year, m_dt.month, 3),
            "warehouse_code": "SYNTH_KHO_01",
            "product_code": "SYNTH_SKU_MDF17",
            "partner_code": "SYNTH_SUPP_002",
            "currency": "VND",
            "exchange_rate": 1.0,
            "inward_quantity": 5000.0,
            "inward_value": 2500000000.0,
            "id": inw_id,
            "_source_file": source_file,
            "_loaded_at": fixed_loaded_at,
            "_batch_id": batch_id,
        })
        inw_id += 1

    with engine.connect() as conn:
        for r in inward_rows:
            conn.execute(
                sa.text("""
                    INSERT INTO synthetic.fact_inventoryinward (
                        _id, posting_date, voucher_no, invoice_no, invoice_date, warehouse_code,
                        product_code, partner_code, currency, exchange_rate, inward_quantity, inward_value,
                        id, _source_file, _loaded_at, _batch_id
                    ) VALUES (:_id, :posting_date, :voucher_no, :invoice_no, :invoice_date, :warehouse_code,
                              :product_code, :partner_code, :currency, :exchange_rate, :inward_quantity, :inward_value,
                              :id, :_source_file, :_loaded_at, :_batch_id)
                """),
                r,
            )
        conn.commit()

    # -------------------------------------------------------------------------
    # 16. fact_inventoryoutward
    # -------------------------------------------------------------------------
    outward_rows: list[dict] = []
    outw_id = 1
    for m_dt in MONTH_ENDS:
        ym_str = m_dt.strftime("%Y%m")
        outward_rows.append({
            "_id": outw_id,
            "posting_date": date(m_dt.year, m_dt.month, 18),
            "voucher_no": f"SYNTH_PXK_{ym_str}_01",
            "invoice_no": f"SYNTH_HDOUT_{ym_str}_01",
            "invoice_date": date(m_dt.year, m_dt.month, 18),
            "warehouse_code": "SYNTH_KHO_01",
            "product_code": "SYNTH_SKU_MDF17",
            "partner_code": "SYNTH_CUST_001",
            "currency": "VND",
            "exchange_rate": 1.0,
            "outward_quantity": 4000.0,
            "outward_value": 2000000000.0,
            "id": outw_id,
            "_source_file": source_file,
            "_loaded_at": fixed_loaded_at,
            "_batch_id": batch_id,
        })
        outw_id += 1

    with engine.connect() as conn:
        for r in outward_rows:
            conn.execute(
                sa.text("""
                    INSERT INTO synthetic.fact_inventoryoutward (
                        _id, posting_date, voucher_no, invoice_no, invoice_date, warehouse_code,
                        product_code, partner_code, currency, exchange_rate, outward_quantity, outward_value,
                        id, _source_file, _loaded_at, _batch_id
                    ) VALUES (:_id, :posting_date, :voucher_no, :invoice_no, :invoice_date, :warehouse_code,
                              :product_code, :partner_code, :currency, :exchange_rate, :outward_quantity, :outward_value,
                              :id, :_source_file, :_loaded_at, :_batch_id)
                """),
                r,
            )
        conn.commit()

    # -------------------------------------------------------------------------
    # 17. fact_accountsreceivable (AR)
    # -------------------------------------------------------------------------
    ar_rows: list[dict] = []
    ar_id = 1
    for m_dt in MONTH_ENDS:
        ym_str = m_dt.strftime("%Y%m")
        ar_rows.append({
            "_id": ar_id,
            "posting_date": m_dt,
            "voucher_no": f"SYNTH_BH_{ym_str}_01",
            "invoice_no": f"SYNTH_INV_{ym_str}_01",
            "invoice_date": m_dt,
            "description": f"Hóa đơn bán hàng tháng {m_dt.strftime('%m/%Y')}",
            "partner_code": "SYNTH_CUST_001",
            "reciprocal_account": "5111",
            "debit_amount": 20000000000.0,
            "credit_amount": 0.0,
            "ending_debit_balance": 15000000000.0,
            "ending_credit_balance": 0.0,
            "currency": "VND",
            "exchange_rate": 1.0,
            "id": ar_id,
            "_source_file": source_file,
            "_loaded_at": fixed_loaded_at,
            "_batch_id": batch_id,
        })
        ar_id += 1

    with engine.connect() as conn:
        for r in ar_rows:
            conn.execute(
                sa.text("""
                    INSERT INTO synthetic.fact_accountsreceivable (
                        _id, posting_date, voucher_no, invoice_no, invoice_date, description,
                        partner_code, reciprocal_account, debit_amount, credit_amount, ending_debit_balance,
                        ending_credit_balance, currency, exchange_rate, id, _source_file, _loaded_at, _batch_id
                    ) VALUES (:_id, :posting_date, :voucher_no, :invoice_no, :invoice_date, :description,
                              :partner_code, :reciprocal_account, :debit_amount, :credit_amount, :ending_debit_balance,
                              :ending_credit_balance, :currency, :exchange_rate, :id, :_source_file, :_loaded_at, :_batch_id)
                """),
                r,
            )
        conn.commit()

    # -------------------------------------------------------------------------
    # 18. fact_accountspayable (AP)
    # -------------------------------------------------------------------------
    ap_rows: list[dict] = []
    ap_id = 1
    for m_dt in MONTH_ENDS:
        ym_str = m_dt.strftime("%Y%m")
        ap_rows.append({
            "_id": ap_id,
            "partner_code": "SYNTH_SUPP_001",
            "posting_date": m_dt,
            "voucher_no": f"SYNTH_MH_{ym_str}_01",
            "invoice_no": f"SYNTH_APINV_{ym_str}_01",
            "invoice_date": m_dt,
            "description": f"Hóa đơn mua nguyên vật liệu tháng {m_dt.strftime('%m/%Y')}",
            "reciprocal_account": "152",
            "currency": "VND",
            "exchange_rate": 1.0,
            "debit_amount": 0.0,
            "credit_amount": 18000000000.0,
            "ending_debit_balance": 0.0,
            "ending_credit_balance": 12000000000.0,
            "id": ap_id,
            "_source_file": source_file,
            "_loaded_at": fixed_loaded_at,
            "_batch_id": batch_id,
        })
        ap_id += 1

    with engine.connect() as conn:
        for r in ap_rows:
            conn.execute(
                sa.text("""
                    INSERT INTO synthetic.fact_accountspayable (
                        _id, partner_code, posting_date, voucher_no, invoice_no, invoice_date,
                        description, reciprocal_account, currency, exchange_rate, debit_amount, credit_amount,
                        ending_debit_balance, ending_credit_balance, id, _source_file, _loaded_at, _batch_id
                    ) VALUES (:_id, :partner_code, :posting_date, :voucher_no, :invoice_no, :invoice_date,
                              :description, :reciprocal_account, :currency, :exchange_rate, :debit_amount, :credit_amount,
                              :ending_debit_balance, :ending_credit_balance, :id, :_source_file, :_loaded_at, :_batch_id)
                """),
                r,
            )
        conn.commit()

    # -------------------------------------------------------------------------
    # 19. fact_termdeposit
    # -------------------------------------------------------------------------
    deposits = [
        (1, 1, "SYNTH_STK_001", "SYNTH_VCB", 0.048, 6, 20000000000.0, 20000000000.0, date(2026, 3, 1), date(2026, 9, 1), None, 1),
        (2, 2, "SYNTH_STK_002", "SYNTH_BIDV", 0.052, 12, 15000000000.0, 15000000000.0, date(2026, 1, 15), date(2027, 1, 15), None, 2),
    ]
    with engine.connect() as conn:
        for r in deposits:
            conn.execute(
                sa.text("""
                    INSERT INTO synthetic.fact_termdeposit (
                        _id, stt, passbook_no, bank_code, interest_rate, term, original_amount,
                        remaining_value, deposit_date, maturity_date, settlement_date, id, _source_file, _loaded_at, _batch_id
                    ) VALUES (:id, :stt, :pno, :bcode, :irate, :term, :oamt, :rval, :ddate, :mdate, :sdate, :fid, :src, :lat, :bid)
                """),
                {
                    "id": r[0], "stt": r[1], "pno": r[2], "bcode": r[3], "irate": r[4], "term": r[5],
                    "oamt": r[6], "rval": r[7], "ddate": r[8], "mdate": r[9], "sdate": r[10], "fid": r[11],
                    "src": source_file, "lat": fixed_loaded_at, "bid": batch_id,
                },
            )
        conn.commit()

    # -------------------------------------------------------------------------
    # 20. fact_businessplan
    # -------------------------------------------------------------------------
    plan_rows: list[dict] = []
    plan_id = 1
    for m_dt in MONTH_ENDS:
        plan_rows.append({
            "_id": plan_id,
            "indicator_code": "B02-DN_10",
            "month": m_dt,
            "target_amount": 55000000000.0,
            "_source_file": source_file,
            "_loaded_at": fixed_loaded_at,
            "_batch_id": batch_id,
        })
        plan_id += 1

    with engine.connect() as conn:
        for r in plan_rows:
            conn.execute(
                sa.text("""
                    INSERT INTO synthetic.fact_businessplan (
                        _id, indicator_code, month, target_amount, _source_file, _loaded_at, _batch_id
                    ) VALUES (:_id, :indicator_code, :month, :target_amount, :_source_file, :_loaded_at, :_batch_id)
                """),
                r,
            )
        conn.commit()


def compute_table_checksums(engine: Engine) -> dict[str, str]:
    """Calculate deterministic SHA-256 hash for each synthetic table ordered by _id."""
    checksums: dict[str, str] = {}
    with engine.connect() as conn:
        for tbl in ALL_TABLES:
            res = conn.execute(sa.text(f"SELECT * FROM synthetic.{tbl} ORDER BY _id"))
            hasher = hashlib.sha256()
            for row in res:
                row_str = "|".join("" if v is None else str(v) for v in row)
                hasher.update(row_str.encode("utf-8"))
            checksums[f"synthetic.{tbl}"] = hasher.hexdigest()
    return checksums


def generate_synthetic_warehouse(
    seed: int = 42,
    admin_uri: str | None = None,
    checksum_path: Path | None = None,
) -> dict[str, str]:
    """Generate 12-month synthetic data warehouse deterministically and apply views.

    Args:
        seed: Random seed for deterministic generation (default: 42).
        admin_uri: SQLAlchemy admin URI for gml_synth.
        checksum_path: Destination path for CHECKSUM.txt (EV-03).

    Returns:
        dict[str, str]: Mapping of table names to SHA-256 hex digests.
    """
    settings = _get_settings()
    target_admin_uri = admin_uri or settings.get_admin_uri(profile="synth")
    target_checksum_path = checksum_path or DEFAULT_CHECKSUM_PATH

    # 1. Ensure target database exists
    ensure_database_exists(target_admin_uri)

    # 2. Connect as admin and build synthetic tables
    engine = sa.create_engine(target_admin_uri, pool_pre_ping=True)
    create_synthetic_schema_and_tables(engine)

    # 3. Populate deterministic records
    populate_synthetic_data(engine, seed=seed)

    # 4. Render and apply ai_views on top of synthetic schema
    apply_all(
        admin_uri=target_admin_uri,
        source_schema="synthetic",
        as_of_date="2026-07-31",
    )

    # 5. Compute deterministic table checksums
    checksums = compute_table_checksums(engine)
    engine.dispose()

    # 6. Write EV-03 checksum file
    target_checksum_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "=" * 80,
        "EVIDENCE EV-03: DETERMINISTIC SYNTHETIC WAREHOUSE CHECKSUM (SEED 42)",
        f"Generated at: 2026-07-31T00:00:00Z | Seed: {seed} | Database: gml_synth",
        "=" * 80,
        "",
    ]
    for tbl, sha in sorted(checksums.items()):
        lines.append(f"{tbl}: {sha}")
    lines.append("")

    target_checksum_path.write_text("\n".join(lines), encoding="utf-8")
    return checksums


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic Synthetic Warehouse Generator")
    parser.add_argument("--seed", type=int, default=42, help="Seed for random generator (default: 42)")
    parser.add_argument("--admin-uri", type=str, default=None, help="PostgreSQL Admin URI for gml_synth")
    parser.add_argument("--checksum-path", type=Path, default=None, help="Path for CHECKSUM.txt output")
    args = parser.parse_args()

    print(f"Generating synthetic warehouse (seed={args.seed})...")
    checksums = generate_synthetic_warehouse(
        seed=args.seed,
        admin_uri=args.admin_uri,
        checksum_path=args.checksum_path,
    )
    print(f"Successfully generated {len(checksums)} synthetic tables.")
    print(f"Checksum EV-03 written to: {DEFAULT_CHECKSUM_PATH}")


if __name__ == "__main__":
    main()
