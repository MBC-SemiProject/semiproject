# main.py 연결 시 아래 2줄을 main.py에 추가
# from jin.jin_stock import router as jin_stock_router
# app.include_router(jin_stock_router)

import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, String, create_engine, func, select
from sqlalchemy.engine import URL
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

# 단독 실행(python jin/jin_stock.py) 시에도 상위 폴더의 db.py를 찾을 수 있게 함
sys.path.append(str(Path(__file__).resolve().parent.parent))
from db import Base  # noqa: E402

# 내 로컬 MySQL 접속 정보. 환경이 다르면 여기만 바꾸면 된다.
DB_USER = "root"
DB_PASSWORD = "1234"
DB_NAME = "logistics_db"

# db.py의 engine은 sample_db에 접속하므로 이 파일 전용 engine을 따로 만든다.
# URL.create는 비밀번호에 @, # 같은 특수문자가 있어도 그대로 처리한다.
engine = create_engine(
    URL.create(
        "mysql+mysqlconnector",
        username=DB_USER,
        password=DB_PASSWORD,
        host="localhost",
        port=3306,
        database=DB_NAME,
    )
)


def get_db():
    with Session(engine) as session:
        yield session


SCHEMA = {"schema": DB_NAME}
ITEM_FK = f"{DB_NAME}.items.item_id"
TOP_N = 10


class Item(Base):
    __tablename__ = "items"
    __table_args__ = SCHEMA

    item_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    category: Mapped[str] = mapped_column(String(50))
    zone: Mapped[str] = mapped_column(String(10))


class ItemInventoryStatus(Base):
    __tablename__ = "item_inventory_status"
    __table_args__ = SCHEMA

    item_id: Mapped[str] = mapped_column(ForeignKey(ITEM_FK), primary_key=True)
    stock_level: Mapped[int]
    reorder_point: Mapped[int]
    lead_time_days: Mapped[int]


class ItemPrediction(Base):
    __tablename__ = "item_predictions"
    __table_args__ = SCHEMA

    item_id: Mapped[str] = mapped_column(ForeignKey(ITEM_FK), primary_key=True)
    item_popularity_score: Mapped[float | None]
    forecasted_demand_next_7d: Mapped[float | None]


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    __table_args__ = SCHEMA

    order_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    item_id: Mapped[str] = mapped_column(ForeignKey(ITEM_FK))
    # db.py의 User는 sample_db.users를 가리키므로 ORM FK는 선언하지 않음 (DB의 FK가 검증)
    user_id: Mapped[int | None]
    requested_quantity: Mapped[int]
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    expected_date: Mapped[date | None]
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


SortKey = Literal[
    "zone_asc", "item_id_asc", "urgency_asc", "demand_desc", "popularity_desc"
]

# 정렬 화이트리스트. 모든 기준의 마지막 동점 처리는 item_id ASC
SORT_ORDERS = {
    "zone_asc": [Item.zone.asc(), Item.item_id.asc()],
    "item_id_asc": [Item.item_id.asc()],
    "urgency_asc": [
        # reorder_point = 0이면 NULL이 되어 맨 위로 오므로 COALESCE로 맨 뒤로 보냄
        func.coalesce(
            ItemInventoryStatus.stock_level
            / func.nullif(ItemInventoryStatus.reorder_point, 0),
            999999,
        ).asc(),
        Item.item_id.asc(),
    ],
    "demand_desc": [ItemPrediction.forecasted_demand_next_7d.desc(), Item.item_id.asc()],
    "popularity_desc": [ItemPrediction.item_popularity_score.desc(), Item.item_id.asc()],
}


def build_top10_query(category: str, zone: str, sort_by: str, low_stock_only: bool):
    """조건에 맞는 품목 중 선택한 정렬 기준의 상위 TOP_N건(전체 합계) 조회문."""
    stmt = (
        select(
            Item.item_id,
            Item.category,
            Item.zone,
            ItemInventoryStatus.stock_level,
            ItemInventoryStatus.reorder_point,
            ItemInventoryStatus.lead_time_days,
            ItemPrediction.forecasted_demand_next_7d,
            ItemPrediction.item_popularity_score,
        )
        .join(ItemInventoryStatus, Item.item_id == ItemInventoryStatus.item_id)
        .join(ItemPrediction, Item.item_id == ItemPrediction.item_id)
    )
    if category != "ALL":
        stmt = stmt.where(Item.category == category)
    if zone != "ALL":
        stmt = stmt.where(Item.zone == zone)
    if low_stock_only:
        stmt = stmt.where(
            ItemInventoryStatus.stock_level <= ItemInventoryStatus.reorder_point
        )

    return stmt.order_by(*SORT_ORDERS[sort_by]).limit(TOP_N)


router = APIRouter(prefix="/api", tags=["jin-stock"])


@router.get("/inventory/top10")
def get_inventory_top10(
    category: str = "ALL",
    zone: str = "ALL",
    sort_by: SortKey = "zone_asc",
    low_stock_only: bool = False,
    db: Session = Depends(get_db),
):
    categories = db.scalars(
        select(Item.category).distinct().order_by(Item.category)
    ).all()

    zones = db.scalars(select(Item.zone).distinct().order_by(Item.zone)).all()

    items = []
    query = build_top10_query(category, zone, sort_by, low_stock_only)
    for row in db.execute(query).mappings():
        item = dict(row)
        item["stock_status"] = (
            "재고 부족" if item["stock_level"] <= item["reorder_point"] else "정상"
        )
        items.append(item)

    return {
        "categories": categories,
        "zones": zones,
        "items": items,
        "applied_sort": sort_by,
    }


class PurchaseOrderRequest(BaseModel):
    item_id: str = Field(min_length=1, max_length=50)
    requested_quantity: int = Field(gt=0, le=2_147_483_647)  # MySQL INT 상한
    expected_date: date | None = None
    user_id: int | None = None


@router.post("/purchase-orders", status_code=201)
def create_purchase_order(req: PurchaseOrderRequest, db: Session = Depends(get_db)):
    item = db.get(Item, req.item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="존재하지 않는 품목입니다.")

    expected_date = req.expected_date
    if expected_date is None:
        inventory = db.get(ItemInventoryStatus, item.item_id)
        if inventory is None:
            raise HTTPException(
                status_code=404,
                detail="재고 정보가 없어 입고 예정일을 계산할 수 없습니다.",
            )
        expected_date = date.today() + timedelta(days=inventory.lead_time_days)

    order = PurchaseOrder(
        item_id=item.item_id,
        user_id=req.user_id,
        requested_quantity=req.requested_quantity,
        status="PENDING",
        expected_date=expected_date,
    )
    db.add(order)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="발주를 저장할 수 없습니다. user_id 등 입력값을 확인하세요.",
        )
    db.refresh(order)

    return {
        "order_id": order.order_id,
        "item_id": order.item_id,
        "user_id": order.user_id,
        "requested_quantity": order.requested_quantity,
        "status": order.status,
        "expected_date": order.expected_date,
        "created_at": order.created_at,
    }


if __name__ == "__main__":
    import uvicorn
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 단독 테스트 전용. 인증이 없으므로 외부에 공개하지 말 것
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    uvicorn.run(app, host="127.0.0.1", port=8000)
