import pytest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.optimize import calculate_rop, calculate_eoq

def test_eoq_standard():
    # Demand = 10,000 cái/năm. Đặt hàng = $50. Lưu kho = 2 (rate=0.2, cost=10 -> H=2)
    # EOQ = sqrt(2 * 10000 * 50 / 2) = sqrt(500000) = 707.106...
    # Làm tròn ceil -> 708
    eoq = calculate_eoq(annual_demand=10000, ordering_cost=50, holding_cost_rate=0.2, unit_cost=10)
    assert eoq == 708

def test_safety_stock():
    # Std Demand = 10. Lead time = 4 ngày. Z (95%) ~ 1.645
    # SS = 1.645 * 10 * sqrt(4) = 1.645 * 10 * 2 = 32.9
    # Ceil -> 33
    rop, ss = calculate_rop(avg_demand=20, std_demand=10, lead_time_days=4, service_level=0.95)
    assert ss == 33

def test_rop_logic():
    # Avg Demand = 20. Lead time = 4. SS = 33 (như test trên)
    # ROP = (20 * 4) + 33 = 80 + 33 = 113
    rop, ss = calculate_rop(avg_demand=20, std_demand=10, lead_time_days=4, service_level=0.95)
    assert rop == 113

def test_negative_values():
    with pytest.raises(ValueError):
        calculate_rop(-5, 10, 4)
    with pytest.raises(ValueError):
        calculate_eoq(100, -10, 0.2, 10)
