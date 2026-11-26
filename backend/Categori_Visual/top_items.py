import os
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import create_engine, text

router = APIRouter(prefix="/api/category", tags=["Category Top Items"])

DEFAULT_SQLITE_PATH = Path(__file__).resolve().parent.parent / "semiproject.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}")
engine = create_engine(DATABASE_URL)

TopItemMetric = Literal["avg_daily_demand", "avg_std_dev", "avg_forecast_7d"]

TOP_ITEM_SORT_COLS: dict[str, str] = {
    "avg_daily_demand": "avg_daily_demand",
    "avg_std_dev": "avg_std_dev",
    "avg_forecast_7d": "avg_forecast_7d",
}

TOP_ITEMS_SQL = """
    SELECT
        i.item_id AS item_id,
        i.category AS category,
        ROUND(COALESCE(p.daily_demand, 0), 2) AS avg_daily_demand,
        ROUND(COALESCE(p.demand_std_dev, 0), 2) AS avg_std_dev,
        ROUND(COALESCE(p.forecasted_demand_next_7d, 0), 2) AS avg_forecast_7d
    FROM items i
    LEFT JOIN item_predictions p ON i.item_id = p.item_id
    {where_clause}
    ORDER BY {order_col} DESC
    LIMIT :limit
"""


@router.get("/top-items")
def get_top_items(
    metric: TopItemMetric = Query(
        default="avg_forecast_7d",
        description="정렬 기준: avg_daily_demand, avg_std_dev, avg_forecast_7d",
    ),
    limit: int = Query(default=10, ge=1, le=100, description="상위 N개 (기본 10)"),
    category: Optional[str] = Query(default=None, description="특정 카테고리만 필터링 (선택)"),
):
    order_col = TOP_ITEM_SORT_COLS.get(metric, "avg_forecast_7d")
    where_clause = "WHERE i.category = :category" if category else ""
    query = text(TOP_ITEMS_SQL.format(where_clause=where_clause, order_col=order_col))

    params: dict[str, object] = {"limit": limit}
    if category:
        params["category"] = category

    try:
        with engine.connect() as conn:
            rows = conn.execute(query, params).mappings().all()
            data = [dict(row) for row in rows]

        return {
            "source": "database",
            "metric": order_col,
            "limit": limit,
            "count": len(data),
            "data": data,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"상위 품목 조회 실패: {e}",
        )