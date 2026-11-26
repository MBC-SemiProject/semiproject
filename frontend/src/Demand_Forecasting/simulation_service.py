import math
import random
from typing import Optional

DEFAULT_LEAD_TIME_DAYS = 7


def build_trajectory(start_stock: float, adj_demand_7d: float, safety_stock: float):
    daily = adj_demand_7d / 7.0
    first_caution_day: Optional[str] = None
    first_risk_day: Optional[str] = None
    rows = []

    for day in range(1, 8):
        cum_demand = daily * day
        rem = start_stock - cum_demand
        day_status = "적정"
        if rem < 0:
            day_status = "위험"
            if first_risk_day is None:
                first_risk_day = f"D+{day}"
        elif rem < safety_stock:
            day_status = "주의"
            if first_caution_day is None:
                first_caution_day = f"D+{day}"

        rows.append(
            {
                "day": f"D+{day}",
                "cum_demand": round(cum_demand, 2),
                "proj_remaining_stock": round(rem, 2),
                "day_status": day_status,
            }
        )

    return first_caution_day, first_risk_day, rows


def run_predict_7d(
    stock_level: float,
    forecasted_demand_next_7d: float,
    demand_std_dev: float,
    lead_time_days: float,
    demand_growth: float,
    safety_factor: float,
    unit_price: float,
):
    adj_demand_7d = round(forecasted_demand_next_7d * (1.0 + demand_growth), 2)
    safety_stock = round(safety_factor * demand_std_dev * math.sqrt(lead_time_days), 2)
    required_stock_7d = round(adj_demand_7d + safety_stock, 2)
    stock_gap_7d = round(stock_level - required_stock_7d, 2)
    recommended_order_qty = max(0, math.ceil(required_stock_7d - stock_level))

    if stock_level < adj_demand_7d:
        status_7d = "위험"
        reason_7d = (
            f"현재고({stock_level:.1f})가 조정 7일 예상 수요({adj_demand_7d:.1f})보다 적어 "
            "7일 이내 재고 부족 위험이 있습니다."
        )
    elif stock_level < required_stock_7d:
        status_7d = "주의"
        reason_7d = (
            f"7일 예상 수요({adj_demand_7d:.1f})는 감당 가능하지만, "
            f"안전재고({safety_stock:.2f})를 포함한 필요 재고({required_stock_7d:.2f})에는 부족합니다."
        )
    else:
        status_7d = "적정"
        reason_7d = (
            f"현재고({stock_level:.1f})가 조정 7일 수요와 안전재고를 합한 "
            f"필요 재고({required_stock_7d:.2f}) 이상으로 안정적입니다."
        )

    first_caution_day, first_risk_day, trajectory = build_trajectory(
        stock_level, adj_demand_7d, safety_stock
    )
    _, _, after_order_trajectory = build_trajectory(
        stock_level + recommended_order_qty, adj_demand_7d, safety_stock
    )

    return {
        "status_7d": status_7d,
        "reason_7d": reason_7d,
        "first_caution_day": first_caution_day,
        "first_risk_day": first_risk_day,
        "adj_demand_7d": adj_demand_7d,
        "safety_stock": safety_stock,
        "required_stock_7d": required_stock_7d,
        "stock_gap_7d": stock_gap_7d,
        "recommended_order_qty": recommended_order_qty,
        "est_order_cost": round(recommended_order_qty * unit_price),
        "daily_trajectory": trajectory,
        "after_order_trajectory": after_order_trajectory,
    }


def build_realtime_7d_series(
    items: list[dict],
    category: str = "ALL",
    zone: str = "ALL",
    demand_growth: float = -0.05,
    live_stream: bool = True,
):
    weights = [0.69, 0.81, 0.93, 1.18, 1.04, 1.07, 1.25]
    ratios = [0.95, 0.96, 0.93, 0.96, 0.95, 0.98, 0.96]
    jitter = random.uniform(0.96, 1.04) if live_stream else 1.0

    filtered = items
    if category and category != "ALL":
        filtered = [i for i in filtered if i.get("category") == category]
    if zone and zone != "ALL":
        filtered = [i for i in filtered if i.get("zone") == zone]

    base_sum = sum(float(i.get("forecasted_demand_next_7d", 0.0)) for i in filtered)
    total_7d = base_sum * (1.0 + demand_growth) * jitter
    avg_daily = total_7d / 7.0
    forecast_series = [round(avg_daily * w) for w in weights]
    actual_series = [round(val * ratios[idx]) for idx, val in enumerate(forecast_series)]

    return {
        "labels": ["11/20", "11/21", "11/22", "11/23", "11/24", "11/25", "11/26"],
        "forecast_series": forecast_series,
        "actual_series": actual_series,
        "total_7d_forecast": round(total_7d, 2),
    }