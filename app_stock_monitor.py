from pathlib import Path
import pandas as pd
import streamlit as st

FILE = Path("output/긴급발주알림리스트.xlsx")

st.set_page_config(page_title="Logistics AI", layout="wide")

# 디자인
st.markdown("""
<style>
.stApp {background:#0f172a;color:#e2e8f0}
h1,h2,h3 {color:#f8fafc!important}
div[data-testid="stMetric"] {
    background:#1e293b;padding:18px;border-radius:12px;
    border:1px solid #334155
}
div[data-testid="stMetricValue"] {color:#34d399}
section[data-testid="stSidebar"] {background:#111827}
</style>
""", unsafe_allow_html=True)

# 데이터
if not FILE.exists():
    st.error("엑셀 파일이 없습니다. urgent_stock_monitor.py를 먼저 실행하세요.")
    st.stop()

try:
    df = pd.read_excel(FILE, sheet_name="Category_Top10")
    all_df = pd.read_excel(FILE, sheet_name="All_Analysis")
except Exception as e:
    st.error(f"엑셀 읽기 오류: {e}")
    st.stop()

# 헤더
st.caption("LOGISTICS AI SYSTEM | MODULE 01")
st.title("📦 실시간 재고 모니터링")
st.caption("재주문점 이하 품목 및 카테고리별 긴급 발주 현황")

# KPI
c1, c2, c3, c4 = st.columns(4)
c1.metric("전체 품목", f"{len(all_df):,}개")
c2.metric("긴급 발주 대상", f"{len(all_df[all_df.stock_level <= all_df.reorder_point]):,}개")
c3.metric("표시 품목", f"{len(df):,}개")
c4.metric("카테고리", f"{df.category.nunique()}개")

# 필터
st.sidebar.title("🔎 재고 필터")
category = st.sidebar.selectbox("카테고리", ["전체"] + sorted(df.category.dropna().unique()))
zone = st.sidebar.selectbox("구역", ["전체"] + sorted(df.zone.dropna().astype(str).unique()))
search = st.sidebar.text_input("품목 ID 검색")

view = df.copy()
if category != "전체":
    view = view[view.category == category]
if zone != "전체":
    view = view[view.zone.astype(str) == zone]
if search:
    view = view[view.item_id.astype(str).str.contains(search, case=False, na=False)]

# 긴급 발주 테이블
st.subheader("🚨 카테고리별 긴급 발주 상위 10개")
cols = [
    "카테고리순위", "item_id", "category", "zone",
    "stock_level", "reorder_point", "재고부족량",
    "예상재고소진일", "lead_time_days",
    "stockout_count_last_month", "우선순위", "권장발주시점"
]
st.dataframe(view[[c for c in cols if c in view.columns]],
             use_container_width=True, hide_index=True)

# 카테고리 분포
st.subheader("📊 카테고리별 발주 대상 분포")
urgent = all_df[all_df.stock_level <= all_df.reorder_point]
st.bar_chart(urgent.groupby("category").size().sort_values(ascending=False))

# 결품 이력
st.subheader("⚠️ 전월 결품 이력 상위 10개")
stockout = all_df.sort_values("stockout_count_last_month", ascending=False).head(10)
cols = ["item_id", "category", "zone", "stockout_count_last_month",
        "stock_level", "reorder_point"]
st.dataframe(stockout[[c for c in cols if c in stockout.columns]],
             use_container_width=True, hide_index=True)

# 엑셀 다운로드
st.download_button("📥 엑셀 다운로드", FILE.read_bytes(),
                   file_name=FILE.name,
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
