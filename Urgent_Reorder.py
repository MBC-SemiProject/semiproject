from pathlib import Path
import pandas as pd
import numpy as np

INPUT_FILE = Path("logistics_data_preprocessed_review.xlsx")
OUTPUT_DIR = Path("output")
OUTPUT_FILE = OUTPUT_DIR / "긴급발주알림리스트.xlsx"

CATEGORIES = ["Pharma", "Automotive", "Electronics", "Groceries", "Apparel"]

def build_alerts():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"원본 파일을 찾을 수 없습니다: {INPUT_FILE}\n"
            "프로젝트 폴더에 엑셀 파일을 복사하거나 INPUT_FILE 경로를 수정하세요."
        )

    df = pd.read_excel(INPUT_FILE, sheet_name="Preprocessed_Data")

    required = [
        "item_id", "category", "zone", "stock_level", "reorder_point",
        "reorder_frequency_days", "lead_time_days", "daily_demand",
        "stockout_count_last_month", "forecasted_demand_next_7d"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"엑셀에 필요한 컬럼이 없습니다: {missing}")

    numeric_cols = [
        "stock_level", "reorder_point", "reorder_frequency_days",
        "lead_time_days", "daily_demand", "stockout_count_last_month",
        "forecasted_demand_next_7d"
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["item_id", "category", "stock_level", "reorder_point"]).copy()

    # 재주문점 이하 품목만 긴급 발주 후보로 선정
    alerts = df[df["stock_level"] <= df["reorder_point"]].copy()
    alerts["재고부족량"] = (alerts["reorder_point"] - alerts["stock_level"]).clip(lower=0)
    alerts["재고부족률"] = np.where(
        alerts["reorder_point"] > 0,
        alerts["재고부족량"] / alerts["reorder_point"],
        0
    )
    alerts["예상재고소진일"] = np.where(
        alerts["daily_demand"] > 0,
        alerts["stock_level"] / alerts["daily_demand"],
        np.inf
    )
    alerts["납품기간재고부족"] = (
        alerts["예상재고소진일"] < alerts["lead_time_days"]
    )
    alerts["7일수요초과"] = (
        alerts["forecasted_demand_next_7d"] > alerts["stock_level"]
    )

    # 우선순위: 납품 전 결품 위험 -> 재고 부족률 -> 전월 결품 이력
    alerts["긴급도점수"] = (
        alerts["납품기간재고부족"].astype(int) * 100
        + alerts["재고부족률"].fillna(0) * 50
        + alerts["stockout_count_last_month"].fillna(0) * 5
        + alerts["7일수요초과"].astype(int) * 10
    )
    alerts["우선순위"] = np.select(
        [
            alerts["납품기간재고부족"],
            alerts["stock_level"] <= alerts["reorder_point"],
            alerts["7일수요초과"]
        ],
        ["긴급", "위험", "주의"],
        default="정상"
    )
    alerts["권장발주시점"] = np.where(
        alerts["납품기간재고부족"],
        "즉시 발주",
        np.where(alerts["재고부족률"] > 0.5, "우선 발주", "발주 검토")
    )

    # 카테고리별 긴급도 상위 10개
    alerts = alerts.sort_values(
        ["category", "긴급도점수", "재고부족량"],
        ascending=[True, False, False]
    )
    alerts["카테고리순위"] = alerts.groupby("category").cumcount() + 1
    top10 = alerts[alerts["카테고리순위"] <= 10].copy()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        alerts.to_excel(writer, sheet_name="All_Analysis", index=False)
        top10.to_excel(writer, sheet_name="Category_Top10", index=False)
        top10.to_excel(writer, sheet_name="Urgent_Alert_List", index=False)

    print(f"분석 완료: 전체 데이터 {len(df):,}개")
    print(f"재주문점 이하 품목: {len(alerts):,}개")
    print("카테고리별 재주문 대상 수:")
    print(alerts["category"].value_counts().reindex(CATEGORIES, fill_value=0))
    print(f"카테고리별 상위 10개: 최대 {len(top10):,}개")
    print(f"엑셀 저장 위치: {OUTPUT_FILE.resolve()}")

if __name__ == "__main__":
    build_alerts()
