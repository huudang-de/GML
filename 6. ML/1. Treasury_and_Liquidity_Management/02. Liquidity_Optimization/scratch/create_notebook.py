import json
import os

notebook = {
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# 📊 Khám phá Dữ liệu & Chạy thử Tối ưu hóa Thanh khoản (Liquidity Optimization)\n",
    "\n",
    "Notebook này minh họa quá trình nạp dữ liệu dòng tiền, lãi suất thị trường và thực thi thuật toán Quy hoạch tuyến tính (Linear Programming) bằng thư viện `PuLP`."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "import sys\n",
    "import os\n",
    "import pandas as pd\n",
    "import matplotlib.pyplot as plt\n",
    "\n",
    "# Set path to src\n",
    "sys.path.append(os.path.abspath('..'))\n",
    "from src.data_loader import build_state\n",
    "from src.optimizer import LiquidityOptimizer\n",
    "\n",
    "import warnings\n",
    "warnings.filterwarnings('ignore')"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 1. Nạp 6 luồng dữ liệu (Data Loading)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "state = build_state()\n",
    "print(\"Dòng tiền dự kiến 4 tuần (Adjusted Cashflow):\", state['adjusted_weekly_cashflow'])\n",
    "display(state['credit_limits'].head())\n",
    "display(state['existing_deposits'].head())"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 2. Trực quan hóa Lãi suất Ngân hàng"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "market = state['market_rates']\n",
    "df_3m = market[market['Term'] == '3 Tháng']\n",
    "\n",
    "plt.figure(figsize=(10, 5))\n",
    "for b in df_3m['Bank'].unique():\n",
    "    subset = df_3m[df_3m['Bank'] == b]\n",
    "    plt.bar(b, subset[subset['Type'] == 'Lending']['Interest_Rate'].values[0], color='lightcoral', alpha=0.7, label='Lending (Vay)' if b==df_3m['Bank'].unique()[0] else \"\")\n",
    "    plt.bar(b, subset[subset['Type'] == 'Deposit']['Interest_Rate'].values[0], color='skyblue', label='Deposit (Gửi)' if b==df_3m['Bank'].unique()[0] else \"\")\n",
    "\n",
    "plt.title('Biểu đồ Lãi suất Vay & Gửi Kỳ hạn 3 Tháng (Cập nhật mới nhất)')\n",
    "plt.ylabel('Lãi suất (%/năm)')\n",
    "plt.legend()\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 3. Chạy Thuật toán Tối ưu hóa (PuLP Optimizer)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "optimizer = LiquidityOptimizer(state)\n",
    "result = optimizer.solve(safety_buffer=2e9)\n",
    "\n",
    "if result:\n",
    "    print(\"\\n🎯 TỔNG LÃI VAY ƯỚC TÍNH:\", f\"{result['total_interest_cost']:,.0f} VND/Năm\")\n",
    "    display(result['actions'])"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.11.0"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}

with open("notebooks/1.0-liquidity-optimization-eda.ipynb", "w", encoding="utf-8") as f:
    json.dump(notebook, f, ensure_ascii=False, indent=1)

print("Đã tạo notebook thành công!")
