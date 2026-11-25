from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional

import pandas as pd

DAY_LABELS = ["11/20", "11/21", "11/22", "11/23", "11/24", "11/25", "11/26"]
DAY_WEIGHTS = [0.69, 0.81, 0.93, 1.18, 1.04, 1.07, 1.25]
ACTUAL_RATIOS = [0.95, 0.96, 0.93, 0.96, 0.95, 0.98, 0.96]


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return default
        return int(round(float(val)))
    except (TypeError, ValueError):
        return default


def get_unique_categories(df: pd.DataFrame) -> List[str]:
    if df is None or df.empty or "category" not in df.columns:
        return []
    return sorted({str(c).strip() for c in df["category"].dropna() if str(c).strip()})


def get_top_items_by_category(
    df: pd.DataFrame,
    category: str,
    top_n: int = 10,
    ensure_item_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if df is None or df.empty:
        return []

    sub = df[df["category"].astype(str).str.strip() == str(category).strip()].copy()
    if sub.empty:
        return []

    sort_col = "forecasted_demand_next_7d" if "forecasted_demand_next_7d" in sub.columns else "daily_demand"
    if sort_col in sub.columns:
        sub = sub.sort_values(by=sort_col, ascending=False)

    top_rows = sub.head(top_n).to_dict(orient="records")

    if ensure_item_id and not any(str(r.get("item_id")) == str(ensure_item_id) for r in top_rows):
        matched = sub[sub["item_id"].astype(str) == str(ensure_item_id)]
        if not matched.empty:
            extra = matched.iloc[0].to_dict()
            top_rows = [extra] + top_rows[: max(0, top_n - 1)]

    return top_rows


def predict_7d_and_order(
    stock_level: float,
    forecasted_demand_next_7d: float,
    demand_std_dev: float,
    lead_time_days: float,
    demand_growth: float = 0.0,
    safety_factor: float = 1.5,
    unit_price: float = 100.0,
    handling_cost_per_unit: float = 0.0,
) -> Dict[str, Any]:
    stock = max(0.0, _safe_float(stock_level))
    base_7d = max(0.0, _safe_float(forecasted_demand_next_7d))
    std_dev = max(0.0, _safe_float(demand_std_dev))
    lead_days = max(0.0, _safe_float(lead_time_days))
    growth = max(-1.0, _safe_float(demand_growth))
    sf = max(0.0, _safe_float(safety_factor))
    price = max(0.0, _safe_float(unit_price, 100.0))
    handling = max(0.0, _safe_float(handling_cost_per_unit))

    adj_demand_7d = round(base_7d * (1.0 + growth), 2)
    safety_stock = round(sf * std_dev * math.sqrt(lead_days), 2)
    required_stock_7d = round(adj_demand_7d + safety_stock, 2)
    stock_gap_7d = round(stock - required_stock_7d, 2)
    recommended_order_qty = max(0, math.ceil(required_stock_7d - stock))

    if stock < adj_demand_7d:
        status_7d = "위험"
        reason_7d = (
            f"현재고({stock:.1f})가 조정 7일 예상 수요({adj_demand_7d:.1f})보다 적어 "
            f"7일 이내 재고 부족 위험이 있습니다."
        )
    elif stock < required_stock_7d:
        status_7d = "주의"
        reason_7d = (
            f"7일 예상 수요({adj_demand_7d:.1f})는 감당 가능하지만, "
            f"안전재고({safety_stock:.2f})를 포함한 필요 재고({required_stock_7d:.2f})에는 부족합니다."
        )
    else:
        status_7d = "적정"
        reason_7d = (
            f"현재고({stock:.1f})가 조정 7일 수요와 안전재고를 합한 "
            f"필요 재고({required_stock_7d:.2f}) 이상으로 안정적입니다."
        )

    daily_demand = adj_demand_7d / 7.0 if adj_demand_7d > 0 else 0.0
    first_caution_day: Optional[str] = None
    first_risk_day: Optional[str] = None
    daily_trajectory: List[Dict[str, Any]] = []

    for day in range(1, 8):
        cum_demand = daily_demand * day
        proj_remaining = stock - cum_demand

        if proj_remaining < 0:
            day_status = "위험"
            if first_risk_day is None:
                first_risk_day = f"D+{day}"
        elif proj_remaining < safety_stock:
            day_status = "주의"
            if first_caution_day is None:
                first_caution_day = f"D+{day}"
        else:
            day_status = "적정"

        daily_trajectory.append(
            {
                "day": f"D+{day}",
                "cum_demand": round(cum_demand, 2),
                "proj_remaining_stock": round(proj_remaining, 2),
                "day_status": day_status,
            }
        )

    est_order_cost = round(recommended_order_qty * (price + handling))

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
        "est_order_cost": est_order_cost,
        "daily_trajectory": daily_trajectory,
    }


def build_realtime_7d_series(
    df: pd.DataFrame,
    category: str = "ALL",
    zone: str = "ALL",
    demand_growth: float = 0.0,
    live_stream: bool = True,
) -> Dict[str, Any]:
    if df is None or df.empty:
        return {
            "labels": DAY_LABELS,
            "forecast_series": [0] * 7,
            "actual_series": [0] * 7,
            "total_7d_forecast": 0.0,
        }

    work = df.copy()
    if category and category != "ALL" and "category" in work.columns:
        work = work[work["category"].astype(str) == category]
    if zone and zone != "ALL" and "zone" in work.columns:
        work = work[work["zone"].astype(str) == zone]

    base_sum = sum(_safe_float(r.get("forecasted_demand_next_7d")) for r in work.to_dict(orient="records"))
    jitter = random.uniform(0.96, 1.04) if live_stream else 1.0
    total_7d = base_sum * (1.0 + max(-1.0, _safe_float(demand_growth))) * jitter
    avg_daily = total_7d / 7.0

    forecast_series = [int(round(avg_daily * w)) for w in DAY_WEIGHTS]
    actual_series = [
        int(round(val * ACTUAL_RATIOS[idx] * (random.uniform(0.97, 1.03) if live_stream else 1.0)))
        for idx, val in enumerate(forecast_series)
    ]

    return {
        "labels": DAY_LABELS,
        "forecast_series": forecast_series,
        "actual_series": actual_series,
        "total_7d_forecast": round(total_7d, 2),
    }


def simulate_portfolio(
    df: pd.DataFrame,
    category: str = "ALL",
    zone: str = "ALL",
    status: str = "ALL",
    demand_growth: float = 0.0,
    safety_factor: float = 1.5,
    only_order_needed: bool = False,
) -> Dict[str, Any]:
    if df is None or df.empty:
        return {"rows": [], "chart_by_category": []}

    work = df.copy()
    if category and category != "ALL" and "category" in work.columns:
        work = work[work["category"].astype(str) == category]
    if zone and zone != "ALL" and "zone" in work.columns:
        work = work[work["zone"].astype(str) == zone]

    rows: List[Dict[str, Any]] = []
    for rec in work.to_dict(orient="records"):
        pred = predict_7d_and_order(
            stock_level=_safe_float(rec.get("stock_level")),
            forecasted_demand_next_7d=_safe_float(rec.get("forecasted_demand_next_7d")),
            demand_std_dev=_safe_float(rec.get("demand_std_dev")),
            lead_time_days=_safe_float(rec.get("lead_time_days"), 3.0),
            demand_growth=demand_growth,
            safety_factor=safety_factor,
            unit_price=_safe_float(rec.get("unit_price"), 100.0),
        )
        if status and status != "ALL" and pred["status_7d"] != status:
            continue
        if only_order_needed and pred["recommended_order_qty"] <= 0:
            continue

        rows.append(
            {
                "item_id": rec.get("item_id"),
                "category": rec.get("category"),
                "zone": rec.get("zone"),
                "stock_level": _safe_float(rec.get("stock_level")),
                "base_demand_7d": round(_safe_float(rec.get("forecasted_demand_next_7d")), 2),
                **pred,
            }
        )

    cat_map: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        cat = str(r.get("category") or "Unknown")
        if cat not in cat_map:
            cat_map[cat] = {
                "category": cat,
                "items": 0,
                "base_demand_7d_sum": 0.0,
                "adj_demand_7d_sum": 0.0,
                "recommended_order_qty_sum": 0,
            }
        cat_map[cat]["items"] += 1
        cat_map[cat]["base_demand_7d_sum"] += _safe_float(r.get("base_demand_7d"))
        cat_map[cat]["adj_demand_7d_sum"] += _safe_float(r.get("adj_demand_7d"))
        cat_map[cat]["recommended_order_qty_sum"] += _safe_int(r.get("recommended_order_qty"))

    chart_by_category = [
        {
            "category": cat_map[cat]["category"],
            "items": cat_map[cat]["items"],
            "base_demand_7d_sum": round(cat_map[cat]["base_demand_7d_sum"], 2),
            "adj_demand_7d_sum": round(cat_map[cat]["adj_demand_7d_sum"], 2),
            "recommended_order_qty_sum": cat_map[cat]["recommended_order_qty_sum"],
        }
        for cat in sorted(cat_map.keys())
    ]

    return {"rows": rows, "chart_by_category": chart_by_category}