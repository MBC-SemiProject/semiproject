import { useEffect, useState } from "react";
import "../App.css";
import "../css/JinStockList.css";

// 백엔드(jin_stock.py) 주소. 배포 환경이 다르면 이 값만 바꾸면 됩니다.
const API_BASE = "http://localhost:8000";

const SORT_OPTIONS = [
  { value: "zone_asc", label: "창고 구역 알파벳순 (기본)" },
  { value: "item_id_asc", label: "품목 ID 오름차순" },
  { value: "urgency_asc", label: "재고 부족 긴급도순" },
  { value: "demand_desc", label: "AI 7일 예측수요 높은 순" },
  { value: "popularity_desc", label: "인기도 점수 높은 순" },
];

const isLowStock = (item) => item.stock_level <= item.reorder_point;

const recommendedQuantity = (item) =>
  Math.max(
    Math.ceil((item.forecasted_demand_next_7d ?? 0) * 2 - item.stock_level),
    item.reorder_point - item.stock_level + 50,
    10
  );

async function requestJson(url, options) {
  const response = await fetch(url, options);
  const body = await response.json().catch(() => null);
  if (!response.ok || body === null) {
    const detail = typeof body?.detail === "string" ? body.detail : null;
    throw new Error(detail ?? `요청에 실패했습니다. (HTTP ${response.status})`);
  }
  return body;
}

function OrderPanel({ item, onClose }) {
  const [quantity, setQuantity] = useState(String(recommendedQuantity(item)));
  const [submitting, setSubmitting] = useState(false);
  const [order, setOrder] = useState(null);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    const requested = Number(quantity);
    if (!Number.isInteger(requested) || requested <= 0) {
      setError("발주 수량은 1 이상의 정수로 입력하세요.");
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      const created = await requestJson(`${API_BASE}/api/purchase-orders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ item_id: item.item_id, requested_quantity: requested }),
      });
      setOrder(created);
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="jin-order">
      <p className="jin-order-title">발주 시뮬레이션: {item.item_id}</p>
      <p>
        현재고: {item.stock_level} / 재주문점: {item.reorder_point} / 리드타임:{" "}
        {item.lead_time_days}일
      </p>
      <p>권장 발주 수량: {recommendedQuantity(item)}</p>
      <label>
        발주 수량{" "}
        <input
          type="number"
          min="1"
          step="1"
          value={quantity}
          disabled={submitting || order !== null}
          onChange={(e) => setQuantity(e.target.value)}
        />
      </label>
      <button
        type="button"
        className="jin-btn"
        disabled={submitting || order !== null}
        onClick={handleSubmit}
      >
        {submitting ? "요청 중..." : "발주 확정"}
      </button>
      <button
        type="button"
        className="jin-btn jin-btn-secondary"
        disabled={submitting}
        onClick={onClose}
      >
        닫기
      </button>
      {error && (
        <p role="alert" className="jin-message jin-error">
          {error}
        </p>
      )}
      {order && (
        <p role="status" className="jin-message jin-success">
          발주가 접수되었습니다. (발주번호 {order.order_id}, 수량 {order.requested_quantity},
          상태 {order.status}, 입고 예정일 {order.expected_date})
        </p>
      )}
    </div>
  );
}

function JinStockList() {
  const [category, setCategory] = useState("ALL");
  const [zone, setZone] = useState("ALL");
  const [sortBy, setSortBy] = useState("zone_asc");
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [categories, setCategories] = useState([]);
  const [zones, setZones] = useState([]);
  const [result, setResult] = useState({ query: null, items: [], error: "" });
  const [selectedId, setSelectedId] = useState(null);

  const query = new URLSearchParams({
    category,
    zone,
    sort_by: sortBy,
    low_stock_only: String(lowStockOnly),
  }).toString();
  const loading = result.query !== query;

  useEffect(() => {
    // 조건을 빠르게 바꿀 때 이전 응답이 최신 결과를 덮어쓰지 않도록 취소
    const controller = new AbortController();

    requestJson(`${API_BASE}/api/inventory/top10?${query}`, { signal: controller.signal })
      .then((data) => {
        if (controller.signal.aborted) return;
        setCategories(data.categories);
        // 수정 전 백엔드가 아직 실행 중이면 zones가 없으므로 빈 목록으로 처리
        setZones(data.zones ?? []);
        setResult({ query, items: data.items, error: "" });
      })
      .catch((e) => {
        if (controller.signal.aborted) return;
        setResult({ query, items: [], error: e.message });
      });

    return () => controller.abort();
  }, [query]);

  // 조회 조건이 바뀌면 열려 있던 발주 영역은 닫음
  const changeFilter = (setter, value) => {
    setter(value);
    setSelectedId(null);
  };

  return (
    <div className="jin-stock">
      <h2>창고 재고 현황 목록 (Items Master)</h2>
      <p className="jin-desc">재주문점 이하 품목은 '재고 부족'으로 표시되며 즉시 발주 시뮬레이션이 가능합니다.</p>
      <p className="jin-desc">선택한 조건과 정렬 기준의 상위 10개 품목만 표시합니다.</p>

      <div className="jin-controls">
        <label>
          카테고리{" "}
          <select value={category} onChange={(e) => changeFilter(setCategory, e.target.value)}>
            <option value="ALL">전체 카테고리</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </label>

        <label>
          창고 구역{" "}
          <select value={zone} onChange={(e) => changeFilter(setZone, e.target.value)}>
            <option value="ALL">전체 구역</option>
            {zones.map((z) => (
              <option key={z} value={z}>
                {z}
              </option>
            ))}
          </select>
        </label>

        <label>
          정렬 기준{" "}
          <select value={sortBy} onChange={(e) => changeFilter(setSortBy, e.target.value)}>
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label>
          <input
            type="checkbox"
            checked={lowStockOnly}
            onChange={(e) => changeFilter(setLowStockOnly, e.target.checked)}
          />
          재고 부족 품목만 보기
        </label>
      </div>

      {loading && (
        <p role="status" className="jin-message">
          불러오는 중...
        </p>
      )}
      {!loading && result.error && (
        <p role="alert" className="jin-message jin-error">
          {result.error}
        </p>
      )}

      {!loading && !result.error && (
        <div className="jin-table-wrap">
          <table>
            <thead>
              <tr>
                <th>품목 ID</th>
                <th>카테고리</th>
                <th>창고 구역</th>
                <th className="jin-num">현재고</th>
                <th className="jin-num">재주문점</th>
                <th className="jin-num">AI 7일 예측수요</th>
                <th>재고 상태</th>
                <th>액션</th>
              </tr>
            </thead>
            <tbody>
              {result.items.length === 0 && (
                <tr>
                  <td colSpan={8} className="jin-empty">조건에 맞는 품목이 없습니다.</td>
                </tr>
              )}
              {result.items.flatMap((item) => {
                const row = (
                  <tr key={item.item_id}>
                    <td className="jin-id">{item.item_id}</td>
                    <td>{item.category}</td>
                    <td>{item.zone}</td>
                    <td className="jin-num">{item.stock_level}</td>
                    <td className="jin-num">{item.reorder_point}</td>
                    <td className="jin-num">{item.forecasted_demand_next_7d?.toFixed(2) ?? "-"}</td>
                    <td>
                      <span className={`jin-badge ${isLowStock(item) ? "jin-badge-low" : "jin-badge-ok"}`}>
                        {isLowStock(item) ? "재고 부족" : "정상"}
                      </span>
                    </td>
                    <td>
                      <button
                        type="button"
                        className="jin-btn"
                        onClick={() => setSelectedId(item.item_id)}
                      >
                        발주 시뮬레이션
                      </button>
                    </td>
                  </tr>
                );
                if (item.item_id !== selectedId) return [row];
                return [
                  row,
                  <tr key={`${item.item_id}-order`}>
                    <td colSpan={8}>
                      <OrderPanel item={item} onClose={() => setSelectedId(null)} />
                    </td>
                  </tr>,
                ];
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default JinStockList;
