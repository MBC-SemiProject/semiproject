import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Chart,
  BarController,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
} from "chart.js";
import {
  Calculator,
  Cpu,
  ShoppingCart,
  SlidersHorizontal,
} from "lucide-react";

Chart.register(
  BarController,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip
);

const API_BASE_URL = "http://127.0.0.1:8000";
const DEFAULT_LEAD_TIME_DAYS = 7;

const INITIAL_ITEMS = [
  {
    item_id: "ITM10149",
    category: "Pharma",
    zone: "A",
    stock_level: 115,
    reorder_point: 140,
    lead_time_days: 7,
    daily_demand: 28.5,
    demand_std_dev: 9.08,
    unit_price: 100.0,
    forecasted_demand_next_7d: 200.0,
    default_growth: 13,
    default_safety: 1.6,
  },
  {
    item_id: "ITM10001",
    category: "Pharma",
    zone: "B",
    stock_level: 340,
    reorder_point: 150,
    lead_time_days: 7,
    daily_demand: 31.5,
    demand_std_dev: 6.2,
    unit_price: 45.0,
    forecasted_demand_next_7d: 229.8,
    default_growth: 0,
    default_safety: 1.5,
  },
  {
    item_id: "ITM10000",
    category: "Electronics",
    zone: "A",
    stock_level: 85,
    reorder_point: 120,
    lead_time_days: 7,
    daily_demand: 24.0,
    demand_std_dev: 9.51,
    unit_price: 120.0,
    forecasted_demand_next_7d: 182.27,
    default_growth: 10,
    default_safety: 1.5,
  },
  {
    item_id: "ITM10002",
    category: "Automotive",
    zone: "C",
    stock_level: 42,
    reorder_point: 90,
    lead_time_days: 7,
    daily_demand: 15.2,
    demand_std_dev: 5.4,
    unit_price: 210.0,
    forecasted_demand_next_7d: 114.5,
    default_growth: 0,
    default_safety: 1.5,
  },
  {
    item_id: "ITM10003",
    category: "Groceries",
    zone: "D",
    stock_level: 520,
    reorder_point: 200,
    lead_time_days: 7,
    daily_demand: 62.0,
    demand_std_dev: 14.8,
    unit_price: 18.5,
    forecasted_demand_next_7d: 456.2,
    default_growth: 0,
    default_safety: 1.5,
  },
  {
    item_id: "ITM10004",
    category: "Apparel",
    zone: "A",
    stock_level: 110,
    reorder_point: 130,
    lead_time_days: 7,
    daily_demand: 19.0,
    demand_std_dev: 7.1,
    unit_price: 65.0,
    forecasted_demand_next_7d: 143.65,
    default_growth: 0,
    default_safety: 1.5,
  },
];

function buildTrajectory(startStock, adjDemand7d, safetyStock) {
  const daily = adjDemand7d / 7;
  let firstCautionDay = null;
  let firstRiskDay = null;
  const rows = [];

  for (let day = 1; day <= 7; day += 1) {
    const cumDemand = Number((daily * day).toFixed(2));
    const rem = Number((startStock - cumDemand).toFixed(2));
    let dayStatus = "적정";

    if (rem < 0) {
      dayStatus = "위험";
      if (!firstRiskDay) firstRiskDay = `D+${day}`;
    } else if (rem < safetyStock) {
      dayStatus = "주의";
      if (!firstCautionDay) firstCautionDay = `D+${day}`;
    }

    rows.push({
      day: `D+${day}`,
      cum_demand: cumDemand,
      proj_remaining_stock: rem,
      day_status: dayStatus,
    });
  }

  return { firstCautionDay, firstRiskDay, rows };
}

function calculateLocalSimulation({
  stockLevel,
  baseDemand7d,
  stdDev,
  leadTimeDays,
  growthPercent,
  safetyFactor,
  unitPrice,
}) {
  const stock = Math.max(0, Number(stockLevel) || 0);
  const base7d = Math.max(0, Number(baseDemand7d) || 0);
  const std = Math.max(0, Number(stdDev) || 0);
  const lead = Math.max(0, Number(leadTimeDays) || 0);
  const growth = Math.max(-1, (Number(growthPercent) || 0) / 100);
  const sf = Math.max(0, Number(safetyFactor) || 0);
  const price = Math.max(0, Number(unitPrice) || 0);

  const adjDemand7d = Number((base7d * (1 + growth)).toFixed(2));
  const safetyStock = Number((sf * std * Math.sqrt(lead)).toFixed(2));
  const requiredStock7d = Number((adjDemand7d + safetyStock).toFixed(2));
  const stockGap7d = Number((stock - requiredStock7d).toFixed(2));
  const recommendedOrderQty = Math.max(0, Math.ceil(requiredStock7d - stock));
  const estOrderCost = Math.round(recommendedOrderQty * price);

  let status7d = "적정";
  let reason7d = `현재고(${stock.toFixed(1)})가 조정 7일 수요와 안전재고를 합한 필요 재고(${requiredStock7d.toFixed(2)}) 이상으로 안정적입니다.`;

  if (stock < adjDemand7d) {
    status7d = "위험";
    reason7d = `현재고(${stock.toFixed(1)})가 조정 7일 예상 수요(${adjDemand7d.toFixed(1)})보다 적어 7일 이내 재고 부족 위험이 있습니다.`;
  } else if (stock < requiredStock7d) {
    status7d = "주의";
    reason7d = `7일 예상 수요(${adjDemand7d.toFixed(1)})는 감당 가능하지만, 안전재고(${safetyStock.toFixed(2)})를 포함한 필요 재고(${requiredStock7d.toFixed(2)})에는 부족합니다.`;
  }

  const beforeTraj = buildTrajectory(stock, adjDemand7d, safetyStock);
  const afterTraj = buildTrajectory(
    stock + recommendedOrderQty,
    adjDemand7d,
    safetyStock
  );

  return {
    status_7d: status7d,
    reason_7d: reason7d,
    first_caution_day: beforeTraj.firstCautionDay,
    first_risk_day: beforeTraj.firstRiskDay,
    adj_demand_7d: adjDemand7d,
    safety_stock: safetyStock,
    required_stock_7d: requiredStock7d,
    stock_gap_7d: stockGap7d,
    recommended_order_qty: recommendedOrderQty,
    est_order_cost: estOrderCost,
    daily_trajectory: beforeTraj.rows,
    after_order_trajectory: afterTraj.rows,
  };
}

function StatusPill({ status }) {
  if (status === "위험") {
    return (
      <span className="inline-flex px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
        위험
      </span>
    );
  }
  if (status === "주의") {
    return (
      <span className="inline-flex px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
        주의
      </span>
    );
  }
  return (
    <span className="inline-flex px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
      적정
    </span>
  );
}

export default function DemandForecastingSimulator({ onCreateOrder }) {
  const [items, setItems] = useState(INITIAL_ITEMS);
  const [selectedCategory, setSelectedCategory] = useState("Pharma");
  const [selectedItemId, setSelectedItemId] = useState("ITM10149");

  const [stockLevel, setStockLevel] = useState(115);
  const [baseDemand7d, setBaseDemand7d] = useState(200.0);
  const [demand7dInput, setDemand7dInput] = useState("226.00");
  const [demandStdDev, setDemandStdDev] = useState(9.08);
  const [leadTimeDays, setLeadTimeDays] = useState(DEFAULT_LEAD_TIME_DAYS);
  const [growthPercent, setGrowthPercent] = useState(13);
  const [safetyFactor, setSafetyFactor] = useState(1.6);
  const [targetDay, setTargetDay] = useState(7);
  const [toastMessage, setToastMessage] = useState("");

  const [simResult, setSimResult] = useState(() =>
    calculateLocalSimulation({
      stockLevel: 115,
      baseDemand7d: 200.0,
      stdDev: 9.08,
      leadTimeDays: DEFAULT_LEAD_TIME_DAYS,
      growthPercent: 13,
      safetyFactor: 1.6,
      unitPrice: 100.0,
    })
  );

  const chartCanvasRef = useRef(null);
  const chartInstanceRef = useRef(null);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage((prev) => (prev === msg ? "" : prev));
    }, 2600);
  };

  useEffect(() => {
    let active = true;
    fetch(`${API_BASE_URL}/api/items?limit=100`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!active || !Array.isArray(data?.items) || data.items.length === 0) {
          return;
        }
        const normalized = data.items.map((row) => ({
          item_id: String(row.item_id),
          category: String(row.category || "General"),
          zone: String(row.zone || "A"),
          stock_level: Number(row.stock_level ?? 0),
          reorder_point: Number(row.reorder_point ?? 100),
          lead_time_days: DEFAULT_LEAD_TIME_DAYS,
          daily_demand: Number(row.daily_demand ?? 20),
          demand_std_dev: Number(row.demand_std_dev ?? 8),
          unit_price: Number(row.unit_price ?? 100),
          forecasted_demand_next_7d: Number(row.forecasted_demand_next_7d ?? 140),
          default_growth: Number(row.default_growth ?? 0),
          default_safety: Number(row.default_safety ?? 1.5),
        }));
        setItems(normalized);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  const categories = useMemo(() => {
    const set = new Set(items.map((i) => i.category).filter(Boolean));
    return Array.from(set).sort();
  }, [items]);

  const top10Items = useMemo(() => {
    return items
      .filter((i) => i.category === selectedCategory)
      .sort(
        (a, b) =>
          Number(b.forecasted_demand_next_7d || 0) -
          Number(a.forecasted_demand_next_7d || 0)
      )
      .slice(0, 10);
  }, [items, selectedCategory]);

  const activeItem = useMemo(() => {
    return (
      top10Items.find((i) => i.item_id === selectedItemId) ||
      items.find((i) => i.item_id === selectedItemId) ||
      top10Items[0] ||
      items[0]
    );
  }, [top10Items, items, selectedItemId]);

  const applyItemDefaults = (item) => {
    if (!item) return;
    const initGrowth =
      item.item_id === "ITM10149" ? 13 : Number(item.default_growth ?? 0);
    const initSafety =
      item.item_id === "ITM10149" ? 1.6 : Number(item.default_safety ?? 1.5);
    const initBase7d = Number(item.forecasted_demand_next_7d ?? 140);
    const initAdj7d = Number(
      (initBase7d * (1 + initGrowth / 100)).toFixed(2)
    );

    setSelectedItemId(item.item_id);
    setStockLevel(Number(item.stock_level ?? 0));
    setBaseDemand7d(initBase7d);
    setDemand7dInput(initAdj7d.toFixed(2));
    setDemandStdDev(Number(item.demand_std_dev ?? 8));
    setLeadTimeDays(DEFAULT_LEAD_TIME_DAYS);
    setGrowthPercent(initGrowth);
    setSafetyFactor(initSafety);
  };

  const handleCategoryChange = (nextCat) => {
    setSelectedCategory(nextCat);
    const candidates = items
      .filter((i) => i.category === nextCat)
      .sort(
        (a, b) =>
          Number(b.forecasted_demand_next_7d || 0) -
          Number(a.forecasted_demand_next_7d || 0)
      );
    if (candidates[0]) {
      applyItemDefaults(candidates[0]);
    }
  };

  const handleDemand7dInputChange = (rawValue) => {
    setDemand7dInput(rawValue);
    const parsed = parseFloat(rawValue);
    if (Number.isNaN(parsed) || parsed < 0) return;
    const factor = 1 + (Number(growthPercent) || 0) / 100;
    setBaseDemand7d(factor !== 0 ? parsed / factor : parsed);
  };

  const handleDemand7dBlur = () => {
    const parsed = parseFloat(demand7dInput);
    if (!Number.isNaN(parsed) && parsed >= 0) {
      setDemand7dInput(parsed.toFixed(2));
    } else {
      setDemand7dInput(simResult.adj_demand_7d.toFixed(2));
    }
  };

  const applyPreset = (preset) => {
    if (preset === "danger") {
      setStockLevel(65);
      setBaseDemand7d(210);
      setDemand7dInput("241.50");
      setDemandStdDev(12.5);
      setLeadTimeDays(DEFAULT_LEAD_TIME_DAYS);
      setGrowthPercent(15);
      setSafetyFactor(1.5);
    } else if (preset === "caution") {
      setStockLevel(195);
      setBaseDemand7d(180);
      setDemand7dInput("189.00");
      setDemandStdDev(10.0);
      setLeadTimeDays(DEFAULT_LEAD_TIME_DAYS);
      setGrowthPercent(5);
      setSafetyFactor(1.5);
    } else if (preset === "safe") {
      setStockLevel(420);
      setBaseDemand7d(160);
      setDemand7dInput("160.00");
      setDemandStdDev(7.0);
      setLeadTimeDays(DEFAULT_LEAD_TIME_DAYS);
      setGrowthPercent(0);
      setSafetyFactor(1.5);
    } else {
      applyItemDefaults(activeItem);
      showToast("선택 품목의 기본값으로 초기화했습니다.");
    }
  };

  useEffect(() => {
    const payload = {
      stock_level: Math.max(0, Number(stockLevel) || 0),
      forecasted_demand_next_7d: Math.max(0, Number(baseDemand7d) || 0),
      demand_std_dev: Math.max(0, Number(demandStdDev) || 0),
      lead_time_days: Math.max(0, Number(leadTimeDays) || 0),
      demand_growth: (Number(growthPercent) || 0) / 100,
      safety_factor: Math.max(0, Number(safetyFactor) || 0),
      unit_price: Number(activeItem?.unit_price ?? 100),
    };

    const fallback = calculateLocalSimulation({
      stockLevel: payload.stock_level,
      baseDemand7d: payload.forecasted_demand_next_7d,
      stdDev: payload.demand_std_dev,
      leadTimeDays: payload.lead_time_days,
      growthPercent: Number(growthPercent) || 0,
      safetyFactor: payload.safety_factor,
      unitPrice: payload.unit_price,
    });

    let cancelled = false;
    fetch(`${API_BASE_URL}/api/predict-7d`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (cancelled) return;
        if (data && Array.isArray(data.daily_trajectory)) {
          const afterRows =
            Array.isArray(data.after_order_trajectory) &&
            data.after_order_trajectory.length === 7
              ? data.after_order_trajectory
              : buildTrajectory(
                  payload.stock_level + Number(data.recommended_order_qty || 0),
                  Number(data.adj_demand_7d ?? fallback.adj_demand_7d),
                  Number(data.safety_stock ?? fallback.safety_stock)
                ).rows;
          setSimResult({
            ...fallback,
            ...data,
            after_order_trajectory: afterRows,
          });
        } else {
          setSimResult(fallback);
        }
      })
      .catch(() => {
        if (!cancelled) setSimResult(fallback);
      });

    return () => {
      cancelled = true;
    };
  }, [
    stockLevel,
    baseDemand7d,
    demandStdDev,
    leadTimeDays,
    growthPercent,
    safetyFactor,
    activeItem?.unit_price,
  ]);

  useEffect(() => {
    setDemand7dInput(Number(simResult.adj_demand_7d || 0).toFixed(2));
  }, [simResult.adj_demand_7d]);

  const reverseHelper = useMemo(() => {
    const dayNum = Math.max(1, Math.min(7, Number(targetDay) || 7));
    const stock = Math.max(0, Number(stockLevel) || 0);
    const std = Math.max(0, Number(demandStdDev) || 0);
    const lead = Math.max(0, Number(leadTimeDays) || 0);
    const adj7d = Number(simResult.adj_demand_7d || 0);
    const safety = Number(simResult.safety_stock || 0);

    const cumDemandTarget = Number(((adj7d / 7) * dayNum).toFixed(2));
    const beforeStockTarget = Number((stock - cumDemandTarget).toFixed(2));
    const neededStockoutQty = Math.max(0, Math.ceil(cumDemandTarget - stock));
    const neededBufferQty = Math.max(
      0,
      Math.ceil(cumDemandTarget + safety - stock)
    );

    const denom = std * Math.sqrt(lead);
    const requiredSafetyFactor =
      denom > 0
        ? Number(Math.max(0, (stock - cumDemandTarget) / denom).toFixed(1))
        : null;

    let guideText = `D+${dayNum} 누적 수요(${cumDemandTarget.toFixed(2)}개)까지 결품 없이 버티려면 최소 ${neededStockoutQty.toLocaleString()}개(안전재고 확보 시 ${neededBufferQty.toLocaleString()}개)가 필요합니다.`;
    if (neededStockoutQty === 0 && beforeStockTarget >= safety) {
      guideText = `현재고(${stock}개)만으로 D+${dayNum} 시점까지 안전재고(${safety.toFixed(2)}개) 이상을 유지할 수 있어 추가 확보가 불필요합니다.`;
    } else if (neededStockoutQty === 0) {
      guideText = `D+${dayNum} 시점에 소진되지는 않지만, 안전재고를 지키려면 ${neededBufferQty.toLocaleString()}개 추가 확보가 필요합니다.`;
    }

    return {
      dayNum,
      cumDemandTarget,
      beforeStockTarget,
      neededStockoutQty,
      neededBufferQty,
      requiredSafetyFactor,
      guideText,
    };
  }, [
    targetDay,
    stockLevel,
    demandStdDev,
    leadTimeDays,
    simResult.adj_demand_7d,
    simResult.safety_stock,
  ]);

  useEffect(() => {
    const canvas = chartCanvasRef.current;
    if (!canvas) return;
    if (chartInstanceRef.current) {
      chartInstanceRef.current.destroy();
    }

    const safeStock = Math.max(0, Number(stockLevel) || 0);
    const safeAdj = Math.max(0, Number(simResult.adj_demand_7d) || 0);
    const safeQty = Math.max(0, Number(simResult.recommended_order_qty) || 0);

    chartInstanceRef.current = new Chart(canvas.getContext("2d"), {
      type: "bar",
      data: {
        labels: ["현재 보유고", "조정 7일 수요", "권장 발주량"],
        datasets: [
          {
            data: [safeStock, safeAdj, safeQty],
            backgroundColor: [
              "rgba(100, 116, 139, 0.75)",
              "rgba(59, 130, 246, 0.85)",
              "rgba(16, 185, 129, 0.88)",
            ],
            borderColor: ["#94a3b8", "#60a5fa", "#34d399"],
            borderWidth: 1,
            borderRadius: 8,
            maxBarThickness: 44,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#020617",
            borderColor: "#1e293b",
            borderWidth: 1,
            callbacks: {
              label: (ctx) => ` ${Number(ctx.raw).toLocaleString()}개`,
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            border: { color: "#1e293b" },
            ticks: {
              color: "#cbd5e1",
              font: { size: 11, weight: "600" },
            },
          },
          y: {
            beginAtZero: true,
            border: { display: false },
            grid: { color: "rgba(51, 65, 85, 0.28)" },
            ticks: {
              color: "#64748b",
              font: { size: 11 },
              maxTicksLimit: 5,
              callback: (v) => Number(v).toLocaleString(),
            },
          },
        },
      },
    });

    return () => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.destroy();
      }
    };
  }, [stockLevel, simResult.adj_demand_7d, simResult.recommended_order_qty]);

  const handleCreatePurchaseOrder = async () => {
    const qty = Number(simResult.recommended_order_qty || 0);
    if (qty <= 0) {
      showToast("추가 발주 수량이 0개입니다.");
      return;
    }
    const payload = {
      item_id: activeItem?.item_id || "ITM10149",
      requested_quantity: qty,
      status: "PENDING",
    };

    try {
      await fetch(`${API_BASE_URL}/api/purchase-orders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } catch {
      // 오프라인에서도 UI 피드백 제공
    }

    if (typeof onCreateOrder === "function") {
      onCreateOrder(payload);
    }
    showToast(`${payload.item_id} ${qty.toLocaleString()}개 발주 요청을 생성했습니다.`);
  };

  const safeStockNum = Math.max(0, Number(stockLevel) || 0);
  const safeAdjNum = Math.max(0, Number(simResult.adj_demand_7d) || 0);
  const safeOrderNum = Math.max(0, Number(simResult.recommended_order_qty) || 0);
  const postOrderStock = safeStockNum + safeOrderNum;
  const coveragePct =
    safeAdjNum > 0 ? Math.round((safeStockNum / safeAdjNum) * 100) : 100;

  const afterMap = new Map(
    (simResult.after_order_trajectory || []).map((r) => [r.day, r])
  );

  return (
    <div className="space-y-5 text-slate-100">
      {toastMessage && (
        <div className="fixed top-5 right-5 z-50 px-4 py-3 rounded-xl bg-slate-900 border border-emerald-500/50 text-emerald-200 text-xs font-semibold shadow-2xl">
          {toastMessage}
        </div>
      )}

      {/* 상단 헤더 + 품목 선택 + 7일 예상 수요 요약 배너 */}
      <div className="bg-slate-900/95 border border-slate-800 rounded-2xl p-5 sm:p-6 space-y-5">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <span className="text-[11px] font-bold tracking-wider uppercase text-emerald-400">
              ML DEMAND FORECASTING ENGINE
            </span>
            <h2 className="text-lg sm:text-xl font-extrabold text-white mt-0.5">
              품목별 AI 7일 수요 예측 및 발주량 시뮬레이터
            </h2>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <label htmlFor="sim-category" className="text-xs text-slate-400">
              카테고리:
            </label>
            <select
              id="sim-category"
              value={selectedCategory}
              onChange={(e) => handleCategoryChange(e.target.value)}
              className="bg-slate-950 border border-slate-700/90 rounded-xl px-3 py-2 text-xs sm:text-sm font-semibold text-emerald-300 focus:outline-none focus:border-emerald-500"
            >
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>

            <label htmlFor="sim-top-item" className="text-xs text-slate-400">
              상위 10개 물품:
            </label>
            <select
              id="sim-top-item"
              value={activeItem?.item_id || ""}
              onChange={(e) => {
                const found = top10Items.find((i) => i.item_id === e.target.value);
                if (found) applyItemDefaults(found);
              }}
              className="bg-slate-950 border border-slate-700/90 rounded-xl px-3.5 py-2 text-xs sm:text-sm font-semibold text-white focus:outline-none focus:border-emerald-500"
            >
              {top10Items.map((item, idx) => (
                <option key={item.item_id} value={item.item_id}>
                  TOP {idx + 1} · {item.item_id} (7일예측{" "}
                  {Number(item.forecasted_demand_next_7d).toFixed(1)}개)
                </option>
              ))}
            </select>

            <button
              type="button"
              onClick={() => applyPreset("reset")}
              className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold text-slate-200 transition"
            >
              기본값 반영
            </button>
          </div>
        </div>

        <div className="bg-emerald-950/35 border border-emerald-500/40 rounded-2xl p-5 space-y-3.5">
          <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4">
            <div className="flex items-start sm:items-center gap-3.5">
              <div className="w-11 h-11 rounded-xl bg-emerald-500/15 border border-emerald-500/35 flex items-center justify-center text-emerald-400 shrink-0">
                <Cpu className="w-5 h-5" />
              </div>
              <div>
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="text-emerald-300 font-semibold">
                    {activeItem?.item_id} · {activeItem?.category} · Zone{" "}
                    {activeItem?.zone}
                  </span>
                  <StatusPill status={simResult.status_7d} />
                  <span className="text-amber-300 font-semibold">
                    · 주의 진입: {simResult.first_caution_day || "없음"} /
                    소진(위험) 진입: {simResult.first_risk_day || "없음"}
                  </span>
                </div>
                <div className="text-2xl sm:text-3xl font-extrabold text-white mt-1">
                  조정 7일 예상 수요:{" "}
                  <span className="text-emerald-400">
                    {Number(simResult.adj_demand_7d).toFixed(2)}
                  </span>
                  <span className="text-base font-semibold text-slate-200 ml-1">
                    개
                  </span>
                </div>
              </div>
            </div>

            <div className="bg-slate-950/85 border border-slate-800 rounded-xl px-4 py-3 text-xs space-y-1 shrink-0 min-w-[235px]">
              <div className="flex justify-between gap-2">
                <span className="text-slate-400">7일 필요 재고:</span>
                <strong className="text-white font-bold">
                  {Number(simResult.required_stock_7d).toFixed(2)}개
                </strong>
                <span className="text-slate-500">·</span>
                <span className="text-slate-400">안전재고:</span>
                <strong className="text-sky-400 font-bold">
                  {Number(simResult.safety_stock).toFixed(2)}개
                </strong>
              </div>
              <div className="flex justify-end gap-1.5 pt-0.5">
                <span className="text-slate-400">7일 재고 과부족:</span>
                <strong
                  className={
                    simResult.stock_gap_7d < 0
                      ? "text-rose-400 font-bold"
                      : "text-emerald-400 font-bold"
                  }
                >
                  {simResult.stock_gap_7d > 0 ? "+" : ""}
                  {Number(simResult.stock_gap_7d).toFixed(2)}개
                </strong>
              </div>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-slate-950/75 border border-slate-800/90 rounded-xl px-4 py-2.5 text-xs sm:text-sm text-slate-200">
            <span>{simResult.reason_7d}</span>
            <span
              className={`shrink-0 font-bold ${
                simResult.first_risk_day ? "text-rose-300" : "text-emerald-300"
              }`}
            >
              {simResult.first_risk_day
                ? `예상 소진 시점: ${simResult.first_risk_day}`
                : "7일 내 소진 위험 없음"}
            </span>
          </div>
        </div>
      </div>

      {/* 중단 그리드: 좌측 입력/파라미터/역산 보조 + 우측 권장 발주량/차트 */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
        <div className="lg:col-span-7 bg-slate-900/95 border border-slate-800 rounded-2xl p-5 sm:p-6 space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-base sm:text-lg font-bold text-white flex items-center gap-2">
              <SlidersHorizontal className="w-4 h-4 text-emerald-400" />
              <span>숫자 입력 및 파라미터 조절</span>
            </h3>
            <div className="flex flex-wrap items-center gap-1.5">
              <button
                type="button"
                onClick={() => applyPreset("danger")}
                className="px-2.5 py-1 rounded-lg bg-rose-950/80 hover:bg-rose-900 text-rose-300 border border-rose-700/50 text-xs font-semibold"
              >
                위험 예시
              </button>
              <button
                type="button"
                onClick={() => applyPreset("caution")}
                className="px-2.5 py-1 rounded-lg bg-amber-950/80 hover:bg-amber-900 text-amber-300 border border-amber-700/50 text-xs font-semibold"
              >
                주의 예시
              </button>
              <button
                type="button"
                onClick={() => applyPreset("safe")}
                className="px-2.5 py-1 rounded-lg bg-emerald-950/80 hover:bg-emerald-900 text-emerald-300 border border-emerald-700/50 text-xs font-semibold"
              >
                적정 예시
              </button>
              <button
                type="button"
                onClick={() => applyPreset("reset")}
                className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold"
              >
                초기화
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <div>
              <label className="block text-[11px] text-slate-400 mb-1.5">
                현재고 (stock_level)
              </label>
              <input
                type="number"
                min="0"
                step="1"
                value={stockLevel}
                onChange={(e) => setStockLevel(Math.max(0, Number(e.target.value)))}
                className="w-full bg-slate-950 border border-slate-800 focus:border-emerald-500 rounded-xl px-3 py-2 text-sm font-bold text-white focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-[11px] text-slate-400 mb-1.5">
                7일 예상수요
              </label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={demand7dInput}
                onChange={(e) => handleDemand7dInputChange(e.target.value)}
                onBlur={handleDemand7dBlur}
                className="w-full bg-slate-950 border border-slate-800 focus:border-emerald-500 rounded-xl px-3 py-2 text-sm font-bold text-emerald-400 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-[11px] text-slate-400 mb-1.5">
                수요 표준편차
              </label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={demandStdDev}
                onChange={(e) =>
                  setDemandStdDev(Math.max(0, Number(e.target.value)))
                }
                className="w-full bg-slate-950 border border-slate-800 focus:border-emerald-500 rounded-xl px-3 py-2 text-sm font-bold text-white focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-[11px] text-slate-400 mb-1.5">
                리드타임 (일 · 기본 7)
              </label>
              <input
                type="number"
                min="0"
                step="1"
                value={leadTimeDays}
                onChange={(e) =>
                  setLeadTimeDays(Math.max(0, Number(e.target.value)))
                }
                className="w-full bg-slate-950 border border-slate-800 focus:border-emerald-500 rounded-xl px-3 py-2 text-sm font-bold text-white focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-[11px] text-slate-400 mb-1.5">
                산출 안전재고
              </label>
              <input
                type="text"
                readOnly
                value={Number(simResult.safety_stock).toFixed(2)}
                className="w-full bg-slate-950/90 border border-sky-500/50 rounded-xl px-3 py-2 text-sm font-bold text-sky-400 focus:outline-none cursor-default"
              />
            </div>
          </div>

          {/* 수요 증감률 */}
          <div className="bg-slate-950/80 border border-slate-800/90 rounded-xl p-4 space-y-2.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs sm:text-sm font-semibold text-slate-200">
                수요 증감률 조정 (%)
              </span>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min="-100"
                  max="500"
                  step="1"
                  value={growthPercent}
                  onChange={(e) =>
                    setGrowthPercent(
                      Math.max(-100, Math.min(500, Number(e.target.value)))
                    )
                  }
                  className="w-20 bg-slate-900 border border-emerald-500/40 rounded-lg px-2.5 py-1 text-right text-xs font-bold text-emerald-400 focus:outline-none"
                />
                <span className="px-2.5 py-0.5 rounded-md bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 text-xs font-bold">
                  {growthPercent > 0 ? `+${growthPercent}%` : `${growthPercent}%`}
                </span>
              </div>
            </div>
            <input
              type="range"
              min="-20"
              max="50"
              step="1"
              value={Math.max(-20, Math.min(50, growthPercent))}
              onChange={(e) => setGrowthPercent(Number(e.target.value))}
              className="w-full accent-emerald-500 cursor-pointer"
            />
            <div className="flex justify-between text-[11px] text-slate-500">
              <span>-20% (비수기 감소)</span>
              <span>0% (기본 예측)</span>
              <span>+50% (프로모션 급증 · 숫자칸은 -100~500% 직접 입력 가능)</span>
            </div>
          </div>

          {/* 안전재고 계수 */}
          <div className="bg-slate-950/80 border border-slate-800/90 rounded-xl p-4 space-y-2.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs sm:text-sm font-semibold text-slate-200">
                안전재고 계수 (Safety Factor)
              </span>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min="0"
                  max="10"
                  step="0.1"
                  value={safetyFactor}
                  onChange={(e) =>
                    setSafetyFactor(
                      Math.max(0, Math.min(10, Number(e.target.value)))
                    )
                  }
                  className="w-20 bg-slate-900 border border-sky-500/40 rounded-lg px-2.5 py-1 text-right text-xs font-bold text-sky-400 focus:outline-none"
                />
                <span className="px-2.5 py-0.5 rounded-md bg-sky-500/15 text-sky-400 border border-sky-500/30 text-xs font-bold">
                  {Number(safetyFactor).toFixed(1)}
                </span>
              </div>
            </div>
            <input
              type="range"
              min="0.5"
              max="3.0"
              step="0.1"
              value={Math.max(0.5, Math.min(3.0, safetyFactor))}
              onChange={(e) => setSafetyFactor(Number(e.target.value))}
              className="w-full accent-sky-400 cursor-pointer"
            />
            <div className="flex justify-between text-[11px] text-slate-500">
              <span>0.5 (최소 버퍼)</span>
              <span>1.5 (표준 권장)</span>
              <span>3.0 (결품 절대 방지 · 숫자칸은 0~10 직접 입력 가능)</span>
            </div>
          </div>

          {/* 목표 재고일 역산 보조 */}
          <div className="bg-slate-950/85 border border-sky-500/30 rounded-xl p-4 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h4 className="text-xs sm:text-sm font-bold text-white flex items-center gap-1.5">
                  <Calculator className="w-4 h-4 text-sky-400" />
                  <span>목표 재고일 / 목표 잔여일 기준 역산 보조</span>
                </h4>
                <p className="text-[11px] text-slate-400">
                  목표 잔여일(D+n)까지 버티기 위한 필요 추가 수량과 최소 안전재고
                  계수를 역산합니다.
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <label htmlFor="sim-target-day" className="text-xs text-slate-400">
                  목표 일차:
                </label>
                <select
                  id="sim-target-day"
                  value={targetDay}
                  onChange={(e) => setTargetDay(Number(e.target.value))}
                  className="bg-slate-900 border border-sky-500/40 rounded-lg px-2.5 py-1 text-xs font-bold text-sky-300 focus:outline-none"
                >
                  {[1, 2, 3, 4, 5, 6, 7].map((d) => (
                    <option key={d} value={d}>
                      {d === 7 ? "D+7 (7일 전구간)" : `D+${d} (${d}일차)`}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs">
              <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-3">
                <span className="text-[11px] text-slate-400 block">
                  목표일 누적 예상수요
                </span>
                <strong className="text-sm font-bold text-white mt-0.5 block">
                  {reverseHelper.cumDemandTarget.toFixed(2)}개
                </strong>
                <span
                  className={`text-[11px] block mt-0.5 ${
                    reverseHelper.beforeStockTarget < 0
                      ? "text-rose-400 font-semibold"
                      : "text-slate-400"
                  }`}
                >
                  발주 전 D+{reverseHelper.dayNum} 잔여:{" "}
                  {reverseHelper.beforeStockTarget > 0 ? "+" : ""}
                  {reverseHelper.beforeStockTarget.toFixed(2)}개
                </span>
              </div>

              <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-3">
                <span className="text-[11px] text-slate-400 block">
                  결품 방지 추가 필요량
                </span>
                <strong className="text-sm font-bold text-emerald-400 mt-0.5 block">
                  {reverseHelper.neededStockoutQty.toLocaleString()}개
                </strong>
                <span className="text-[11px] text-sky-300 block mt-0.5">
                  안전재고 유지 시: +
                  {reverseHelper.neededBufferQty.toLocaleString()}개
                </span>
              </div>

              <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-3 flex flex-col justify-between">
                <div>
                  <span className="text-[11px] text-slate-400 block">
                    목표일 안전재고 계수
                  </span>
                  <strong className="text-sm font-bold text-amber-300 mt-0.5 block">
                    {reverseHelper.requiredSafetyFactor !== null
                      ? reverseHelper.requiredSafetyFactor.toFixed(1)
                      : "계산 불가"}
                  </strong>
                </div>
                <button
                  type="button"
                  disabled={reverseHelper.requiredSafetyFactor === null}
                  onClick={() => {
                    if (reverseHelper.requiredSafetyFactor !== null) {
                      setSafetyFactor(reverseHelper.requiredSafetyFactor);
                      showToast(
                        `안전재고 계수(${reverseHelper.requiredSafetyFactor.toFixed(1)})를 적용했습니다.`
                      );
                    }
                  }}
                  className="mt-1.5 w-full py-1 rounded bg-sky-500/15 hover:bg-sky-500/25 disabled:opacity-40 text-sky-300 border border-sky-500/35 text-[11px] font-semibold transition"
                >
                  계수 바로 적용
                </button>
              </div>
            </div>

            <p className="text-xs text-sky-200/90 bg-slate-900/70 border border-slate-800/80 rounded-lg px-3 py-2">
              {reverseHelper.guideText}
            </p>
          </div>
        </div>

        {/* 우측: OPTIMAL ORDER QUANTITY + 비교 차트 */}
        <div className="lg:col-span-5 flex flex-col gap-5">
          <div className="bg-gradient-to-br from-emerald-500 to-emerald-700 rounded-2xl p-6 text-white shadow-xl flex flex-col justify-between">
            <div>
              <span className="inline-block px-2.5 py-0.5 rounded-md bg-black/20 text-[10px] font-bold tracking-wider uppercase text-emerald-100">
                OPTIMAL ORDER QUANTITY
              </span>
              <h3 className="text-sm font-semibold text-emerald-50 mt-2.5">
                시뮬레이션 최종 권장 발주량
              </h3>
              <div className="flex items-baseline gap-1.5 mt-1">
                <span className="text-4xl sm:text-5xl font-extrabold tracking-tight">
                  {Number(simResult.recommended_order_qty).toLocaleString()}
                </span>
                <span className="text-lg font-bold text-emerald-100">개</span>
              </div>
              <p className="text-xs text-emerald-100/90 mt-2">
                예상 발주 금액: $
                {Number(simResult.est_order_cost).toLocaleString()} (단가 $
                {activeItem?.unit_price ?? 100})
              </p>
            </div>
            <button
              type="button"
              onClick={handleCreatePurchaseOrder}
              className="mt-5 w-full py-3 rounded-xl bg-slate-950/90 hover:bg-slate-900 text-emerald-400 font-bold text-xs sm:text-sm flex items-center justify-center gap-2 transition"
            >
              <ShoppingCart className="w-4 h-4" />
              <span>이 수량으로 즉시 발주 요청 생성</span>
            </button>
          </div>

          <div className="bg-slate-900/95 border border-slate-800 rounded-2xl p-5 flex-1 flex flex-col justify-between gap-3.5">
            <div className="flex items-center justify-between gap-2">
              <h4 className="text-xs sm:text-sm font-bold text-white">
                현재고 vs 조정 7일 수요 vs 권장발주량
              </h4>
              <span
                className={`px-2 py-0.5 rounded-md text-[11px] font-semibold border ${
                  coveragePct < 100
                    ? "bg-rose-500/15 text-rose-300 border-rose-500/30"
                    : "bg-emerald-500/15 text-emerald-300 border-emerald-500/30"
                }`}
              >
                7일 수요 커버 {coveragePct}%
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="bg-slate-950/85 border border-slate-800/90 rounded-xl px-2.5 py-2">
                <span className="block text-[10px] text-slate-400">
                  현재 보유고
                </span>
                <strong className="block text-xs sm:text-sm font-extrabold text-slate-200 mt-0.5">
                  {safeStockNum.toLocaleString()}개
                </strong>
              </div>
              <div className="bg-slate-950/85 border border-slate-800/90 rounded-xl px-2.5 py-2">
                <span className="block text-[10px] text-slate-400">
                  조정 7일 수요
                </span>
                <strong className="block text-xs sm:text-sm font-extrabold text-blue-400 mt-0.5">
                  {safeAdjNum.toFixed(1)}개
                </strong>
              </div>
              <div className="bg-slate-950/85 border border-slate-800/90 rounded-xl px-2.5 py-2">
                <span className="block text-[10px] text-slate-400">
                  권장 발주량
                </span>
                <strong className="block text-xs sm:text-sm font-extrabold text-emerald-400 mt-0.5">
                  {safeOrderNum.toLocaleString()}개
                </strong>
              </div>
            </div>

            <div className="relative h-48 w-full">
              <canvas ref={chartCanvasRef} />
            </div>

            <div className="pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
              <span>발주 후 예상 총 보유고</span>
              <strong className="text-emerald-300 font-bold">
                {postOrderStock.toLocaleString()}개
              </strong>
            </div>
          </div>
        </div>
      </div>

      {/* 하단 D+1 ~ D+7 일별 소진 추이 통합 표 */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
        <div className="p-5 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h4 className="text-base font-bold text-white">
              D+1 ~ D+7 일별 소진 추이 및 소진 시점 하이라이트
            </h4>
            <p className="text-xs text-slate-400 mt-0.5">
              발주 전 기준 잔여재고와 권장 발주량 반영 후 잔여재고를 한 표에서
              함께 비교합니다.
            </p>
          </div>
          <span className="px-3 py-1 rounded-full text-xs font-bold bg-rose-500/15 text-rose-300 border border-rose-500/30 self-start sm:self-auto">
            최초 진입: 주의 {simResult.first_caution_day || "없음"} · 위험{" "}
            {simResult.first_risk_day || "없음"}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="bg-slate-950/60 border-b border-slate-800 text-[11px] uppercase text-slate-400">
                <th className="py-3 px-5">경과 일차</th>
                <th className="py-3 px-4 text-right">누적 예상 수요</th>
                <th className="py-3 px-4 text-right">발주 전 잔여재고</th>
                <th className="py-3 px-4 text-right text-emerald-300">
                  발주 후 잔여재고
                </th>
                <th className="py-3 px-4 text-center">상태</th>
                <th className="py-3 px-5">소진/주의 진입 포인트</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70">
              {(simResult.daily_trajectory || []).map((row) => {
                const isFirstCaution = row.day === simResult.first_caution_day;
                const isFirstRisk = row.day === simResult.first_risk_day;
                const afterRow = afterMap.get(row.day) || {
                  proj_remaining_stock:
                    Number(row.proj_remaining_stock) + safeOrderNum,
                };

                let rowClass = "";
                let pointNode = <span className="text-xs text-slate-500">-</span>;

                if (isFirstRisk) {
                  rowClass =
                    "bg-rose-950/45 ring-1 ring-inset ring-rose-500/40";
                  pointNode = (
                    <span className="px-2.5 py-1 rounded-md bg-rose-500/20 text-rose-300 border border-rose-500/40 text-xs font-bold">
                      소진(위험) 최초 진입
                    </span>
                  );
                } else if (isFirstCaution) {
                  rowClass =
                    "bg-amber-950/35 ring-1 ring-inset ring-amber-500/35";
                  pointNode = (
                    <span className="px-2.5 py-1 rounded-md bg-amber-500/20 text-amber-300 border border-amber-500/40 text-xs font-bold">
                      주의 구간 최초 진입
                    </span>
                  );
                } else if (row.day_status === "위험") {
                  rowClass = "bg-rose-950/15";
                  pointNode = (
                    <span className="text-xs text-rose-400/90 font-medium">
                      소진 지속
                    </span>
                  );
                } else if (row.day_status === "주의") {
                  pointNode = (
                    <span className="text-xs text-amber-400/90 font-medium">
                      안전재고 미만 유지
                    </span>
                  );
                }

                const beforeColor =
                  row.proj_remaining_stock < 0
                    ? "text-rose-400 font-bold"
                    : row.day_status === "주의"
                    ? "text-amber-300 font-semibold"
                    : "text-white font-semibold";

                const afterColor =
                  afterRow.proj_remaining_stock < 0
                    ? "text-rose-400 font-bold"
                    : afterRow.proj_remaining_stock < simResult.safety_stock
                    ? "text-amber-300 font-semibold"
                    : "text-emerald-300 font-bold";

                return (
                  <tr key={row.day} className={rowClass}>
                    <td className="py-3 px-5 font-bold text-white">{row.day}</td>
                    <td className="py-3 px-4 text-right text-slate-300">
                      {Number(row.cum_demand).toFixed(2)}개
                    </td>
                    <td className={`py-3 px-4 text-right ${beforeColor}`}>
                      {Number(row.proj_remaining_stock).toFixed(2)}개
                    </td>
                    <td className={`py-3 px-4 text-right ${afterColor}`}>
                      {Number(afterRow.proj_remaining_stock).toFixed(2)}개
                    </td>
                    <td className="py-3 px-4 text-center">
                      <StatusPill status={row.day_status} />
                    </td>
                    <td className="py-3 px-5">{pointNode}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="px-5 py-3 bg-slate-950/50 border-t border-slate-800/80 text-[11px] text-slate-500">
          ※ 조정 7일 예상 수요를 7일로 나눈 기준의 일별 추이이며, &ldquo;발주
          후 잔여재고&rdquo;는 현재고에 권장 발주 수량을 더한 기준입니다(권장
          발주량이 0개면 발주 전과 동일).
        </div>
      </div>
    </div>
  );
}