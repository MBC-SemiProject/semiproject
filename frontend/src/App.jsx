import React from "react";
import DemandForecastingSimulator from "./DemandForecastingSimulator";

export default function App() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 sm:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        <DemandForecastingSimulator
          onCreateOrder={(order) => {
            console.log("생성된 발주 요청:", order);
          }}
        />
      </div>
    </div>
  );
}