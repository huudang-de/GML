import pulp
import pandas as pd
import numpy as np

class LiquidityOptimizer:
    def __init__(self, state):
        self.state = state
        self.prob = pulp.LpProblem("Liquidity_Optimization", pulp.LpMinimize)
        
    def _extract_rates(self):
        # Lấy lãi suất kỳ hạn 3 Tháng làm chuẩn cho vay ngắn hạn
        market = self.state['market_rates']
        market = market[market['Term'] == '3 Tháng']
        
        rates = {}
        for _, row in market.iterrows():
            bank = row['Bank']
            if bank not in rates:
                rates[bank] = {}
            if row['Type'] == 'Lending':
                rates[bank]['Normal_Lending'] = row['Interest_Rate']
            else:
                # Lãi cầm cố = Lãi tiền gửi + 2.0% biên độ (Giả định thực tế VN)
                rates[bank]['CashBacked_Lending'] = row['Interest_Rate'] + 2.0
        return rates

    def solve(self, safety_buffer=1e9):
        # 1. Tính toán Vốn cần gọi (Target Capital)
        cf = self.state['adjusted_weekly_cashflow']
        # Tính luỹ kế dòng tiền để tìm ra điểm "đáy" (Max Deficit)
        cumulative = np.cumsum(cf)
        max_deficit = -min(min(cumulative), 0)
        
        target_capital = max_deficit + safety_buffer
        print(f"📊 Phân tích Dòng tiền: Thâm hụt tối đa = {max_deficit:,.0f} VND")
        print(f"🎯 Mục tiêu huy động vốn (Bao gồm Buffer) = {target_capital:,.0f} VND")
        
        if target_capital == 0:
            print("✅ Công ty dồi dào tiền mặt, không cần vay thêm.")
            return None
            
        # 2. Chuẩn bị Tham số (Parameters)
        rates = self._extract_rates()
        
        banks = self.state['credit_limits']['Bank'].tolist()
        
        avail_credit = {}
        for _, r in self.state['credit_limits'].iterrows():
            avail_credit[r['Bank']] = r['Total_Credit_Limit'] - r['Current_Debt']
            
        avail_cashbacked = {}
        for _, r in self.state['existing_deposits'].iterrows():
            bank = r['Bank']
            max_loan = r['Deposit_Amount'] * r['LTV_Policy']
            avail_cashbacked[bank] = avail_cashbacked.get(bank, 0) + max_loan

        # Lọc danh sách bank có trong market_rates
        valid_banks = [b for b in banks if b in rates]
        
        # 3. Định nghĩa Biến Quyết định (Decision Variables)
        # Vay tín chấp/thế chấp BĐS bình thường
        borrow_normal = {b: pulp.LpVariable(f"Borrow_Normal_{b}", lowBound=0) for b in valid_banks}
        # Vay cầm cố sổ tiết kiệm
        borrow_cashbacked = {b: pulp.LpVariable(f"Borrow_CashBacked_{b}", lowBound=0) for b in valid_banks}
        
        # 4. Hàm mục tiêu: MINIMIZE TỔNG CHI PHÍ LÃI VAY (Objective)
        # Chi phí = Tiền vay * Lãi suất
        total_interest = []
        for b in valid_banks:
            total_interest.append(borrow_normal[b] * (rates[b]['Normal_Lending'] / 100.0))
            if b in avail_cashbacked:
                total_interest.append(borrow_cashbacked[b] * (rates[b]['CashBacked_Lending'] / 100.0))
                
        self.prob += pulp.lpSum(total_interest)
        
        # 5. Ràng buộc (Constraints)
        # Constraint 1: Tổng tiền vay phải bằng Target Capital
        all_borrows = [borrow_normal[b] for b in valid_banks] + \
                      [borrow_cashbacked[b] for b in valid_banks if b in avail_cashbacked]
        self.prob += pulp.lpSum(all_borrows) == target_capital, "Meet_Target_Capital"
        
        # Constraint 2: Không vượt Hạn mức Tín dụng
        for b in valid_banks:
            self.prob += borrow_normal[b] <= avail_credit[b], f"CreditLimit_{b}"
            
        # Constraint 3: Không vượt LTV Cầm cố sổ tiết kiệm
        for b in valid_banks:
            if b in avail_cashbacked:
                self.prob += borrow_cashbacked[b] <= avail_cashbacked[b], f"LTV_Limit_{b}"
            else:
                self.prob += borrow_cashbacked[b] == 0, f"No_Deposit_{b}"
                
        # 6. Giải bài toán
        self.prob.solve(pulp.PULP_CBC_CMD(msg=0))
        
        # 7. Bóc tách kết quả
        status = pulp.LpStatus[self.prob.status]
        if status != 'Optimal':
            print("❌ Vô nghiệm: Công ty không đủ hạn mức để vay số tiền này!")
            return None
            
        actions = []
        for b in valid_banks:
            val_normal = borrow_normal[b].varValue
            if val_normal > 0:
                actions.append({
                    'Action': 'Vay Hạn mức (Tín chấp/BĐS)',
                    'Bank': b,
                    'Amount_VND': val_normal,
                    'Interest_Rate_%': rates[b]['Normal_Lending']
                })
            
            val_cb = borrow_cashbacked[b].varValue
            if val_cb > 0:
                actions.append({
                    'Action': 'Vay Cầm cố Sổ Tiết Kiệm',
                    'Bank': b,
                    'Amount_VND': val_cb,
                    'Interest_Rate_%': rates[b]['CashBacked_Lending']
                })
                
        df_actions = pd.DataFrame(actions)
        df_actions = df_actions.sort_values('Interest_Rate_%')
        
        return {
            'target_capital': target_capital,
            'total_interest_cost': pulp.value(self.prob.objective),
            'actions': df_actions
        }
