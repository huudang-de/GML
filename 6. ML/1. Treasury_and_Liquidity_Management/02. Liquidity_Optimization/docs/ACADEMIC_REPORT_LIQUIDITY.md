# ACADEMIC REPORT: LIQUIDITY OPTIMIZATION VIA LINEAR PROGRAMMING
**Format:** Scopus Academic Paper (Draft)
**Keywords:** Liquidity Optimization, Linear Programming, Treasury Management, SMEs, PuLP, Cash-backed Loans

## Abstract
Liquidity management in Small and Medium Enterprises (SMEs) in emerging markets like Vietnam involves unique constraints, such as the use of individual collateral (savings books) for corporate loans and varying loan-to-value (LTV) policies across banks. This study proposes a Treasury Intelligence Engine using Linear Programming (LP) to optimize the allocation of idle cash and borrowing needs. By integrating upstream Machine Learning forecasts (Cashflow, Accounts Receivable Risk, and Inventory EOQ), the PuLP-based optimizer minimizes total interest expense. Empirical results from a real-world manufacturing firm (Gỗ Minh Long) demonstrate a significant reduction in interest costs by prioritizing cash-backed loans (4.29% - 4.66%) over standard unsecured corporate loans (7.0% - 8.5%), yielding an estimated annual saving of over 300 million VND for a 10-billion-VND liquidity deficit.

---

## 1. Introduction
Effective treasury management requires balancing liquidity to meet operational needs while maximizing financial returns. Traditional approaches rely on heuristic decision-making, which often leads to sub-optimal capital allocation. In this paper, we present an automated Liquidity Optimization Engine that determines the exact amount to borrow or deposit at specific banks, considering real-world constraints such as credit limits and individual vs. corporate interest rate discrepancies.

## 2. Literature Review & Comparative Analysis
The proposed model is evaluated against three existing frameworks:

1. **FPT Corporation's Cash Sweeping Model (2024):** 
   FPT utilizes a centralized cash pooling strategy to optimize Return on Assets (ROA) across 40+ subsidiaries. While highly effective for conglomerates, it lacks applicability for SMEs where capital often flows between personal (CEO) and corporate entities. Our model introduces the `Owner_Type` constraint to bridge this gap.
2. **Open Source "Cash Liquidity Optimizer" (GitHub):** 
   Existing open-source repositories utilize `PuLP` and `SciPy` for capital allocation. However, they assume static interest rates. Our system dynamically crawls market data (`market_interest_rates.csv`) to capture daily fluctuations in lending and deposit rates.
3. **Vietnamese Manufacturing Study (UEH, 2026):** 
   Recent research from the University of Economics Ho Chi Minh City proposes a hybrid XGBoost-LSTM model coupled with LP. We adopt this "Shift-Left" architecture by decoupling the forecasting components (Cashflow, AR, Inventory) from the optimization engine, feeding pre-processed "clean" data into the LP solver.

## 3. Methodology
The optimization problem is formulated as a Multi-Constraint Linear Programming model solved via the CBC algorithm in the `PuLP` Python library.

**Objective Function:**
$$ \text{Minimize } Z = \sum_{b} \left( X_{b}^{\text{Normal}} \cdot R_{b}^{\text{Normal}} + X_{b}^{\text{CashBacked}} \cdot R_{b}^{\text{CashBacked}} \right) $$

**Constraints:**
1. *Capital Requirement:* $ \sum X_{b} = \text{Max Deficit} + \text{Safety Buffer} $
2. *Credit Line Upper Bound:* $ X_{b}^{\text{Normal}} \le \text{Total\_Limit}_{b} - \text{Current\_Debt}_{b} $
3. *Cash-backed LTV Bound:* $ X_{b}^{\text{CashBacked}} \le \text{Deposit\_Amount}_{b} \times \text{LTV}_{b} $

Data inputs are fetched from a PostgreSQL Data Warehouse (Silver/Gold layers), ensuring that the optimizer processes deterministic values rather than raw, noisy transactional data.

## 4. Empirical Results
The system was tested on the financial data of Gỗ Minh Long for July 2026. The firm faced a projected peak liquidity deficit of 8 billion VND, with a required safety buffer of 2 billion VND (Total Target: 10 billion VND).

**Results:**
- The LP solver converged in $< 0.1$ seconds.
- **Decision:** The algorithm bypassed standard SME loans (7.0% - 8.5%) and fully utilized existing individual savings books at BIDV and Techcombank as collateral.
- **Allocation:** 
  - 9.0 Billion VND borrowed against BIDV savings (Interest: 4.29%)
  - 1.0 Billion VND borrowed against Techcombank savings (Interest: 4.66%)
- **Financial Impact:** Total annual interest expense was optimized to 432.7 million VND, representing a $>40\%$ reduction compared to baseline heuristic borrowing.

## 5. Conclusion & Recommendations
The Liquidity Optimization Engine successfully mathematicalizes the tacit rules of Vietnamese banking (LTVs, individual guarantees) into a robust, scalable Python application. Future work could expand the model into a Multi-Period LP formulation, optimizing capital over a rolling 12-week horizon to account for term structures and yield curves.
