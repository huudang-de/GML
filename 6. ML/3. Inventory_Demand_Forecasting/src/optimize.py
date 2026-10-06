import numpy as np
from scipy.stats import norm
from typing import Tuple

def calculate_rop(avg_demand: float, std_demand: float, lead_time_days: int, service_level: float = 0.95) -> Tuple[int, int]:
    """
    Tính Tồn kho an toàn (Safety Stock) và Điểm đặt hàng lại (ROP).
    Returns: (ROP, Safety Stock)
    """
    if avg_demand < 0 or std_demand < 0 or lead_time_days < 0:
        raise ValueError("Các tham số không được âm")
        
    # Lấy Z-score từ phân phối chuẩn theo Service Level
    z_score = norm.ppf(service_level)
    
    # Công thức Safety Stock
    safety_stock = z_score * std_demand * np.sqrt(lead_time_days)
    
    # Công thức ROP
    rop = (avg_demand * lead_time_days) + safety_stock
    
    # Do hàng hóa (như tấm ván) không thể đặt lẻ (0.5 tấm), ta làm tròn lên thành số nguyên (ceil)
    return int(np.ceil(rop)), int(np.ceil(safety_stock))

def calculate_eoq(annual_demand: float, ordering_cost: float, holding_cost_rate: float, unit_cost: float) -> int:
    """
    Tính Sản lượng đặt hàng kinh tế (EOQ - Economic Order Quantity).
    - annual_demand: Nhu cầu cả năm (D)
    - ordering_cost: Chi phí 1 lần đặt hàng (S)
    - holding_cost_rate: Tỷ lệ chi phí lưu kho trên giá trị hàng (%) 
    - unit_cost: Giá trị 1 đơn vị hàng (C)
    """
    if annual_demand < 0 or ordering_cost < 0 or holding_cost_rate <= 0 or unit_cost <= 0:
        raise ValueError("Tham số không hợp lệ")
        
    holding_cost = holding_cost_rate * unit_cost
    
    eoq = np.sqrt((2 * annual_demand * ordering_cost) / holding_cost)
    
    return int(np.ceil(eoq))
