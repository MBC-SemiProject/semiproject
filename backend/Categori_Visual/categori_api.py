import os
from pathlib import Path
from typing import Literal, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

router = APIRouter(prefix="/api/category", tags=["Category Summary"])

DEFAULT_SQLITE_PATH = Path(__file__).resolve().parent.parent / "semiproject.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}")

engine = create_engine(DATABASE_URL)

MetricType = Literal["avg_daily_demand", "avg_std_dev", "avg_forecast_7d"]


class CategorySummaryItem(BaseModel):
    category: str = Field(..., example="Electronics", description="상품 카테고리명")
    item_count: int = Field(..., example=651, description="카테고리 내 총 품목 수")
    avg_daily_demand: float = Field(..., example=24.71, description="평균 일일 수요")
    avg_std_dev: float = Field(..., example=5.27, description="평균 수요 표준편차(변동성)")
    avg_forecast_7d: float = Field(..., example=157.76, description="평균 7일 예측수요")
    total_stock: int = Field(..., example=172266, description="카테고리 총 현재고")
    est_7d_holding_cost: float = Field(..., example=1259253.87, description="7일 예상 보관 비용")


class CategorySummaryResponse(BaseModel):
    source: str = Field(..., example="database", description="데이터 출처")
    metric: MetricType = Field(..., example="avg_forecast_7d", description="적용된 정렬/분류 지표")
    limit: int = Field(..., example=10, description="최대 조회 개수")
    count: int = Field(..., example=5, description="실제 반환된 건수")
    data: list[CategorySummaryItem]


ALLOWED_METRICS: dict[str, str] = {
    "avg_daily_demand": "avg_daily_demand",
    "avg_std_dev": "avg_std_dev",
    "avg_forecast_7d": "avg_forecast_7d",
}

BASE_SQL = """
    SELECT
        i.category AS category,
        COUNT(i.item_id) AS item_count,
        ROUND(AVG(COALESCE(p.daily_demand, 0)), 2) AS avg_daily_demand,
        ROUND(AVG(COALESCE(p.demand_std_dev, 0)), 2) AS avg_std_dev,
        ROUND(AVG(COALESCE(p.forecasted_demand_next_7d, 0)), 2) AS avg_forecast_7d,
        CAST(COALESCE(SUM(s.stock_level), 0) AS SIGNED) AS total_stock,
        ROUND(SUM(COALESCE(s.stock_level, 0) * COALESCE(i.holding_cost_per_unit_day, 0) * 7), 2) AS est_7d_holding_cost
    FROM items i
    LEFT JOIN item_inventory_status s ON i.item_id = s.item_id
    LEFT JOIN item_predictions p ON i.item_id = p.item_id
    {where_clause}
    GROUP BY i.category
    ORDER BY {order_col} DESC
    LIMIT :limit
"""


@router.get("/top-items")
def get_top_items(
    metric: str = Query(
        default="avg_forecast_7d",
        description="정렬 기준: avg_daily_demand, avg_std_dev, avg_forecast_7d",
    ),
    limit: int = Query(default=10, ge=1, le=100, description="상위 N개 (기본 10)"),
    category: Optional[str] = Query(default=None, description="특정 카테고리만 필터링"),
):
    sort_cols = {
        "avg_daily_demand": "avg_daily_demand",
        "avg_std_dev": "avg_std_dev",
        "avg_forecast_7d": "avg_forecast_7d",
    }
    order_col = sort_cols.get(metric, "avg_forecast_7d")
    where_clause = "WHERE i.category = :category" if category else ""

    sql = text(f"""
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
    """)

    params: dict[str, object] = {"limit": limit}
    if category:
        params["category"] = category

    try:
        with engine.connect() as conn:
            rows = conn.execute(sql, params).mappings().all()
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