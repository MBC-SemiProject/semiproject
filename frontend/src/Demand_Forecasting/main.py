from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from simulation_service import (
    DEFAULT_LEAD_TIME_DAYS,
    build_realtime_7d_series,
    run_predict_7d,
)

app = FastAPI(title="SemiProject B2B Inventory AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ITEMS_DB = [
    {
        "item_id": "ITM10149",
        "category": "Pharma",
        "zone": "A",
        "stock_level": 115,
        "reorder_point": 140,
        "lead_time_days": 7,
        "daily_demand": 28.5,
        "demand_std_dev": 9.08,
        "unit_price": 100.0,
        "forecasted_demand_next_7d": 200.00,
        "default_growth": -5,
        "default_safety": 1.0,
    },
    {
        "item_id": "ITM10000",
        "category": "Electronics",
        "zone": "A",
        "stock_level": 85,
        "reorder_point": 120,
        "lead_time_days": 3,
        "daily_demand": 24.0,
        "demand_std_dev": 9.51,
        "unit_price": 120.0,
        "forecasted_demand_next_7d": 182.27,
        "default_growth": 10,
        "default_safety": 1.5,
    },
    {
        "item_id": "ITM10001",
        "category": "Pharma",
        "zone": "B",
        "stock_level": 340,
        "reorder_point": 150,
        "lead_time_days": 2,
        "daily_demand": 31.5,
        "demand_std_dev": 6.20,
        "unit_price": 45.0,
        "forecasted_demand_next_7d": 229.80,
        "default_growth": 0,
        "default_safety": 1.5,
    },
    {
        "item_id": "ITM10002",
        "category": "Automotive",
        "zone": "C",
        "stock_level": 42,
        "reorder_point": 90,
        "lead_time_days": 5,
        "daily_demand": 15.2,
        "demand_std_dev": 5.40,
        "unit_price": 210.0,
        "forecasted_demand_next_7d": 114.50,
        "default_growth": 0,
        "default_safety": 1.5,
    },
    {
        "item_id": "ITM10003",
        "category": "Groceries",
        "zone": "D",
        "stock_level": 520,
        "reorder_point": 200,
        "lead_time_days": 1,
        "daily_demand": 62.0,
        "demand_std_dev": 14.80,
        "unit_price": 18.5,
        "forecasted_demand_next_7d": 456.20,
        "default_growth": 0,
        "default_safety": 1.5,
    },
    {
        "item_id": "ITM10004",
        "category": "Apparel",
        "zone": "A",
        "stock_level": 110,
        "reorder_point": 130,
        "lead_time_days": 4,
        "daily_demand": 19.0,
        "demand_std_dev": 7.10,
        "unit_price": 65.0,
        "forecasted_demand_next_7d": 143.65,
        "default_growth": 0,
        "default_safety": 1.5,
    },
]

TRANSACTIONS_DB = [
    {
        "transaction_id": 101,
        "item_id": "ITM10149",
        "transaction_type": "OUT",
        "quantity": 25,
        "memo": "수도권 B2B 약국·병원 정기 출고",
    }
]

PURCHASE_ORDERS_DB = [
    {
        "order_id": 501,
        "item_id": "ITM10149",
        "requested_quantity": 110,
        "status": "APPROVED",
    }
]


class Predict7DRequest(BaseModel):
    stock_level: float = Field(..., ge=0)
    forecasted_demand_next_7d: float = Field(..., ge=0)
    demand_std_dev: float = Field(..., ge=0)
    lead_time_days: float = Field(DEFAULT_LEAD_TIME_DAYS, ge=0)
    demand_growth: float = Field(-0.05, ge=-1.0)
    safety_factor: float = Field(1.0, ge=0)
    unit_price: float = Field(100.0, ge=0)


class Realtime7DRequest(BaseModel):
    category: str = "ALL"
    zone: str = "ALL"
    demand_growth: float = -0.05
    live_stream: bool = True


class TransactionCreateRequest(BaseModel):
    item_id: str
    transaction_type: str
    quantity: int = Field(..., gt=0)
    memo: str


class ItemCreateRequest(BaseModel):
    item_id: str
    category: str
    zone: str
    stock_level: int = Field(..., ge=0)
    reorder_point: int = Field(..., ge=1)
    lead_time_days: int = Field(DEFAULT_LEAD_TIME_DAYS, ge=0)
    daily_demand: float = Field(..., gt=0)
    demand_std_dev: float = Field(..., ge=0)
    unit_price: float = Field(..., gt=0)
    forecasted_demand_next_7d: float = Field(..., ge=0)


class PurchaseOrderCreateRequest(BaseModel):
    item_id: str
    requested_quantity: int = Field(..., gt=0)
    status: str = "PENDING"


@app.get("/api/items")
def get_items(
    category: Optional[str] = None,
    top_n: Optional[int] = Query(default=None, ge=1, le=100),
    limit: int = Query(default=100, ge=1, le=1000),
):
    filtered = ITEMS_DB
    if category and category != "ALL":
        filtered = [i for i in filtered if i["category"].lower() == category.lower()]

    if top_n is not None:
        filtered = sorted(
            filtered,
            key=lambda x: float(x.get("forecasted_demand_next_7d", 0)),
            reverse=True,
        )[:top_n]
    else:
        filtered = filtered[:limit]

    return {"items": filtered}


@app.post("/api/items", status_code=201)
def create_item(payload: ItemCreateRequest):
    item_id = payload.item_id.strip().upper()
    if any(i["item_id"] == item_id for i in ITEMS_DB):
        raise HTTPException(status_code=400, detail="이미 존재하는 품목 ID입니다.")

    new_item = {
        "item_id": item_id,
        "category": payload.category,
        "zone": payload.zone,
        "stock_level": payload.stock_level,
        "reorder_point": payload.reorder_point,
        "lead_time_days": payload.lead_time_days,
        "daily_demand": payload.daily_demand,
        "demand_std_dev": payload.demand_std_dev,
        "unit_price": payload.unit_price,
        "forecasted_demand_next_7d": payload.forecasted_demand_next_7d,
        "default_growth": 0,
        "default_safety": 1.5,
    }
    ITEMS_DB.append(new_item)
    return new_item


@app.post("/api/predict-7d")
def predict_7d(req: Predict7DRequest):
    return run_predict_7d(
        stock_level=req.stock_level,
        forecasted_demand_next_7d=req.forecasted_demand_next_7d,
        demand_std_dev=req.demand_std_dev,
        lead_time_days=req.lead_time_days,
        demand_growth=req.demand_growth,
        safety_factor=req.safety_factor,
        unit_price=req.unit_price,
    )


@app.post("/api/realtime-7d")
def realtime_7d(req: Realtime7DRequest):
    return build_realtime_7d_series(
        items=ITEMS_DB,
        category=req.category,
        zone=req.zone,
        demand_growth=req.demand_growth,
        live_stream=req.live_stream,
    )


@app.get("/api/transactions")
def get_transactions(limit: int = Query(default=50, ge=1, le=500)):
    return {"transactions": TRANSACTIONS_DB[:limit]}


@app.post("/api/transactions", status_code=201)
def create_transaction(payload: TransactionCreateRequest):
    tx_type = payload.transaction_type.upper()
    if tx_type not in {"IN", "OUT", "ADJUST"}:
        raise HTTPException(status_code=400, detail="유효하지 않은 거래 유형입니다.")

    item = next((i for i in ITEMS_DB if i["item_id"] == payload.item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="품목을 찾을 수 없습니다.")

    if tx_type == "IN":
        item["stock_level"] += payload.quantity
    elif tx_type == "OUT":
        if item["stock_level"] < payload.quantity:
            raise HTTPException(status_code=400, detail="현재고보다 많은 수량은 출고할 수 없습니다.")
        item["stock_level"] -= payload.quantity
    else:
        item["stock_level"] = payload.quantity

    new_tx = {
        "transaction_id": 100 + len(TRANSACTIONS_DB) + 1,
        "item_id": item["item_id"],
        "transaction_type": tx_type,
        "quantity": payload.quantity,
        "memo": payload.memo,
    }
    TRANSACTIONS_DB.insert(0, new_tx)

    return {
        **new_tx,
        "updated_stock_level": item["stock_level"],
    }


@app.get("/api/purchase-orders")
def get_purchase_orders(limit: int = Query(default=50, ge=1, le=500)):
    return {"purchase_orders": PURCHASE_ORDERS_DB[:limit]}


@app.post("/api/purchase-orders", status_code=201)
def create_purchase_order(payload: PurchaseOrderCreateRequest):
    new_po = {
        "order_id": 500 + len(PURCHASE_ORDERS_DB) + 1,
        "item_id": payload.item_id,
        "requested_quantity": payload.requested_quantity,
        "status": payload.status,
    }
    PURCHASE_ORDERS_DB.insert(0, new_po)
    return new_po