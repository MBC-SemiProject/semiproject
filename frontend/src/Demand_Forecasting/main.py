from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    create_engine,
    select,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from simulation_service import (
    build_realtime_7d_series,
    get_top_items_by_category,
    get_unique_categories,
    predict_7d_and_order,
    simulate_portfolio,
)

MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "1234")
MYSQL_DB = os.getenv("MYSQL_DB", "semiproject_wms")

DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class ItemModel(Base):
    __tablename__ = "items"

    item_id = Column(String(50), primary_key=True, index=True)
    category = Column(String(50), nullable=False, index=True)
    zone = Column(String(20), nullable=False, default="A")
    stock_level = Column(Integer, nullable=False, default=0)
    reorder_point = Column(Integer, nullable=False, default=50)
    lead_time_days = Column(Integer, nullable=False, default=3)
    daily_demand = Column(Float, nullable=False, default=20.0)
    demand_std_dev = Column(Float, nullable=False, default=8.0)
    unit_price = Column(Float, nullable=False, default=100.0)
    forecasted_demand_next_7d = Column(Float, nullable=False, default=140.0)
    default_growth = Column(Integer, nullable=False, default=-5)
    default_safety = Column(Float, nullable=False, default=1.0)


class TransactionModel(Base):
    __tablename__ = "transactions"

    transaction_id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String(50), nullable=False, index=True)
    transaction_type = Column(String(20), nullable=False)  # IN, OUT, ADJUST
    quantity = Column(Integer, nullable=False)
    memo = Column(String(255), nullable=False, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class PurchaseOrderModel(Base):
    __tablename__ = "purchase_orders"

    order_id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String(50), nullable=False, index=True)
    requested_quantity = Column(Integer, nullable=False)
    status = Column(String(30), nullable=False, default="PENDING")
    created_at = Column(DateTime, default=datetime.utcnow)


DEFAULT_ITEMS_DATA = [
    {"item_id": "ITM10149", "category": "Pharma", "zone": "A", "stock_level": 115, "reorder_point": 140, "lead_time_days": 7, "daily_demand": 28.5, "demand_std_dev": 9.08, "unit_price": 100.0, "forecasted_demand_next_7d": 200.00, "default_growth": -5, "default_safety": 1.0},
    {"item_id": "ITM10000", "category": "Electronics", "zone": "A", "stock_level": 85, "reorder_point": 120, "lead_time_days": 3, "daily_demand": 24.0, "demand_std_dev": 9.51, "unit_price": 120.0, "forecasted_demand_next_7d": 182.27, "default_growth": 10, "default_safety": 1.5},
    {"item_id": "ITM10001", "category": "Pharma", "zone": "B", "stock_level": 340, "reorder_point": 150, "lead_time_days": 2, "daily_demand": 31.5, "demand_std_dev": 6.20, "unit_price": 45.0, "forecasted_demand_next_7d": 229.80, "default_growth": 0, "default_safety": 1.5},
    {"item_id": "ITM10002", "category": "Automotive", "zone": "C", "stock_level": 42, "reorder_point": 90, "lead_time_days": 5, "daily_demand": 15.2, "demand_std_dev": 5.40, "unit_price": 210.0, "forecasted_demand_next_7d": 114.50, "default_growth": 0, "default_safety": 1.5},
    {"item_id": "ITM10003", "category": "Groceries", "zone": "D", "stock_level": 520, "reorder_point": 200, "lead_time_days": 1, "daily_demand": 62.0, "demand_std_dev": 14.80, "unit_price": 18.5, "forecasted_demand_next_7d": 456.20, "default_growth": 0, "default_safety": 1.5},
    {"item_id": "ITM10004", "category": "Apparel", "zone": "A", "stock_level": 110, "reorder_point": 130, "lead_time_days": 4, "daily_demand": 19.0, "demand_std_dev": 7.10, "unit_price": 65.0, "forecasted_demand_next_7d": 143.65, "default_growth": 0, "default_safety": 1.5},
]


def init_db_and_seed() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        existing_count = db.query(ItemModel).count()
        if existing_count == 0:
            for row in DEFAULT_ITEMS_DATA:
                db.add(ItemModel(**row))
            db.commit()


def load_items_dataframe() -> pd.DataFrame:
    with SessionLocal() as db:
        rows = db.execute(select(ItemModel)).scalars().all()
        if not rows:
            return pd.DataFrame(columns=[
                "item_id", "category", "zone", "stock_level", "reorder_point",
                "lead_time_days", "daily_demand", "demand_std_dev", "unit_price",
                "forecasted_demand_next_7d", "default_growth", "default_safety",
            ])
        records = [
            {
                "item_id": r.item_id,
                "category": r.category,
                "zone": r.zone,
                "stock_level": r.stock_level,
                "reorder_point": r.reorder_point,
                "lead_time_days": r.lead_time_days,
                "daily_demand": r.daily_demand,
                "demand_std_dev": r.demand_std_dev,
                "unit_price": r.unit_price,
                "forecasted_demand_next_7d": r.forecasted_demand_next_7d,
                "default_growth": r.default_growth,
                "default_safety": r.default_safety,
            }
            for r in rows
        ]
        return pd.DataFrame(records)


app = FastAPI(title="SemiProject B2B Inventory AI API (MySQL)", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db_and_seed()


class Predict7DRequest(BaseModel):
    stock_level: float = Field(..., ge=0)
    forecasted_demand_next_7d: float = Field(..., ge=0)
    demand_std_dev: float = Field(..., ge=0)
    lead_time_days: float = Field(..., ge=0)
    demand_growth: float = Field(0.0, ge=-1.0)
    safety_factor: float = Field(1.5, ge=0)
    unit_price: float = Field(100.0, ge=0)
    handling_cost_per_unit: float = Field(0.0, ge=0)


class SimulateRequest(BaseModel):
    category: str = "ALL"
    zone: str = "ALL"
    status: str = "ALL"
    demand_growth: float = Field(0.0, ge=-1.0)
    safety_factor: float = Field(1.5, ge=0)
    only_order_needed: bool = False


class Realtime7DRequest(BaseModel):
    category: str = "ALL"
    zone: str = "ALL"
    demand_growth: float = Field(0.0, ge=-1.0)
    live_stream: bool = True


class CreateItemRequest(BaseModel):
    item_id: str = Field(..., min_length=1, max_length=50)
    category: str = Field(..., min_length=1, max_length=50)
    zone: str = Field("A", min_length=1, max_length=20)
    stock_level: int = Field(..., ge=0)
    reorder_point: int = Field(..., ge=0)
    lead_time_days: int = Field(3, ge=0)
    daily_demand: float = Field(..., ge=0)
    demand_std_dev: Optional[float] = Field(None, ge=0)
    unit_price: float = Field(..., ge=0)
    forecasted_demand_next_7d: Optional[float] = Field(None, ge=0)


class CreateTransactionRequest(BaseModel):
    item_id: str = Field(..., min_length=1)
    transaction_type: str = Field(..., pattern="^(IN|OUT|ADJUST)$")
    quantity: int = Field(..., ge=0)
    memo: str = Field("", max_length=255)


class CreatePurchaseOrderRequest(BaseModel):
    item_id: str = Field(..., min_length=1)
    requested_quantity: int = Field(..., gt=0)
    status: str = Field("PENDING", max_length=30)


@app.get("/")
def serve_index():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "SemiProject B2B Inventory MySQL API is running"}


@app.get("/health")
def health_check():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    df = load_items_dataframe()
    return {"status": "ok", "database": MYSQL_DB, "rows": len(df)}


@app.get("/api/categories")
def list_categories():
    df = load_items_dataframe()
    return {"categories": get_unique_categories(df)}


@app.get("/api/items")
def list_items(
    limit: int = Query(500, ge=1, le=5000),
    category: Optional[str] = None,
    top_n: Optional[int] = Query(None, ge=1, le=100),
):
    df = load_items_dataframe()
    if category and top_n:
        items = get_top_items_by_category(df, category=category, top_n=top_n)
        return {"items": items, "total": len(items)}

    work = df
    if category and category != "ALL" and "category" in work.columns:
        work = work[work["category"].astype(str) == category]

    items = work.head(limit).to_dict(orient="records")
    return {"items": items, "total": len(work)}


@app.post("/api/items", status_code=201)
def create_item(req: CreateItemRequest):
    item_code = req.item_id.strip().upper()
    with SessionLocal() as db:
        exists = db.query(ItemModel).filter(ItemModel.item_id == item_code).first()
        if exists:
            raise HTTPException(status_code=409, detail=f"Item {item_code} already exists")

        std = req.demand_std_dev if req.demand_std_dev is not None else round(req.daily_demand * 0.35, 2)
        f7d = (
            req.forecasted_demand_next_7d
            if req.forecasted_demand_next_7d is not None
            else round(req.daily_demand * 7.0 + std * 1.5, 2)
        )

        new_item = ItemModel(
            item_id=item_code,
            category=req.category.strip(),
            zone=req.zone.strip(),
            stock_level=req.stock_level,
            reorder_point=req.reorder_point,
            lead_time_days=req.lead_time_days,
            daily_demand=req.daily_demand,
            demand_std_dev=std,
            unit_price=req.unit_price,
            forecasted_demand_next_7d=f7d,
            default_growth=0,
            default_safety=1.5,
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        return {
            "item_id": new_item.item_id,
            "category": new_item.category,
            "zone": new_item.zone,
            "stock_level": new_item.stock_level,
            "reorder_point": new_item.reorder_point,
            "lead_time_days": new_item.lead_time_days,
            "daily_demand": new_item.daily_demand,
            "demand_std_dev": new_item.demand_std_dev,
            "unit_price": new_item.unit_price,
            "forecasted_demand_next_7d": new_item.forecasted_demand_next_7d,
        }


@app.get("/api/items/{item_id}")
def get_item_detail(item_id: str):
    df = load_items_dataframe()
    if "item_id" not in df.columns:
        raise HTTPException(status_code=404, detail="Item not found")
    matched = df[df["item_id"].astype(str) == item_id]
    if matched.empty:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    return matched.iloc[0].to_dict()


@app.get("/api/transactions")
def list_transactions(limit: int = Query(50, ge=1, le=500)):
    with SessionLocal() as db:
        txs = (
            db.query(TransactionModel)
            .order_by(TransactionModel.transaction_id.desc())
            .limit(limit)
            .all()
        )
        return {
            "transactions": [
                {
                    "transaction_id": t.transaction_id,
                    "item_id": t.item_id,
                    "transaction_type": t.transaction_type,
                    "quantity": t.quantity,
                    "memo": t.memo,
                }
                for t in txs
            ]
        }


@app.post("/api/transactions", status_code=201)
def create_transaction(req: CreateTransactionRequest):
    with SessionLocal() as db:
        item = db.query(ItemModel).filter(ItemModel.item_id == req.item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail=f"Item {req.item_id} not found")

        if req.transaction_type == "OUT":
            if item.stock_level < req.quantity:
                raise HTTPException(status_code=400, detail="Insufficient stock")
            item.stock_level -= req.quantity
        elif req.transaction_type == "IN":
            item.stock_level += req.quantity
        elif req.transaction_type == "ADJUST":
            item.stock_level = req.quantity

        tx = TransactionModel(
            item_id=req.item_id,
            transaction_type=req.transaction_type,
            quantity=req.quantity,
            memo=req.memo.strip(),
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        db.refresh(item)
        return {
            "transaction_id": tx.transaction_id,
            "item_id": tx.item_id,
            "transaction_type": tx.transaction_type,
            "quantity": tx.quantity,
            "memo": tx.memo,
            "updated_stock_level": item.stock_level,
        }


@app.get("/api/purchase-orders")
def list_purchase_orders(limit: int = Query(50, ge=1, le=500)):
    with SessionLocal() as db:
        pos = (
            db.query(PurchaseOrderModel)
            .order_by(PurchaseOrderModel.order_id.desc())
            .limit(limit)
            .all()
        )
        return {
            "purchase_orders": [
                {
                    "order_id": p.order_id,
                    "item_id": p.item_id,
                    "requested_quantity": p.requested_quantity,
                    "status": p.status,
                }
                for p in pos
            ]
        }


@app.post("/api/purchase-orders", status_code=201)
def create_purchase_order(req: CreatePurchaseOrderRequest):
    with SessionLocal() as db:
        item = db.query(ItemModel).filter(ItemModel.item_id == req.item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail=f"Item {req.item_id} not found")

        po = PurchaseOrderModel(
            item_id=req.item_id,
            requested_quantity=req.requested_quantity,
            status=req.status,
        )
        db.add(po)
        db.commit()
        db.refresh(po)
        return {
            "order_id": po.order_id,
            "item_id": po.item_id,
            "requested_quantity": po.requested_quantity,
            "status": po.status,
        }


@app.post("/api/predict-7d")
def api_predict_7d(req: Predict7DRequest):
    return predict_7d_and_order(
        stock_level=req.stock_level,
        forecasted_demand_next_7d=req.forecasted_demand_next_7d,
        demand_std_dev=req.demand_std_dev,
        lead_time_days=req.lead_time_days,
        demand_growth=req.demand_growth,
        safety_factor=req.safety_factor,
        unit_price=req.unit_price,
        handling_cost_per_unit=req.handling_cost_per_unit,
    )


@app.post("/api/simulate")
def api_simulate(req: SimulateRequest):
    df = load_items_dataframe()
    return simulate_portfolio(
        df=df,
        category=req.category,
        zone=req.zone,
        status=req.status,
        demand_growth=req.demand_growth,
        safety_factor=req.safety_factor,
        only_order_needed=req.only_order_needed,
    )


@app.post("/api/realtime-7d")
def api_realtime_7d(req: Realtime7DRequest):
    df = load_items_dataframe()
    return build_realtime_7d_series(
        df=df,
        category=req.category,
        zone=req.zone,
        demand_growth=req.demand_growth,
        live_stream=req.live_stream,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)