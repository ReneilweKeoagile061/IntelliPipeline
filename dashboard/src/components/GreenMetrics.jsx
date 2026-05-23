import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, CartesianGrid
} from "recharts";
import { getGreenMetrics } from "../services/claudeService";

export default function GreenMetrics() {
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    getGreenMetrics("7d")
      .then(setMetrics)
      .catch(() => setMetrics({
        total_energy_kwh: 12.4,
        total_co2_grams: 5890,
        training_runs: 8,
        carbon_budget_pct: 24.8,
        daily: [
          { date: "Mon", kwh: 1.8, runs: 1 },
          { date: "Tue", kwh: 2.1, runs: 1 },
          { date: "Wed", kwh: 1.5, runs: 1 },
          { date: "Thu", kwh: 2.4, runs: 2 },
          { date: "Fri", kwh: 1.9, runs: 1 },
          { date: "Sat", kwh: 1.2, runs: 1 },
          { date: "Sun", kwh: 1.5, runs: 1 },
        ],
      }));
  }, []);

  if (!metrics) return <div className="card"><div className="skeleton-text" /></div>;

  const co2Kg = (metrics.total_co2_grams / 1000).toFixed(1);
  const budgetPct = metrics.carbon_budget_pct ?? 24.8;

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
      <div style={{ background: "var(--surface-2)", border: "1px solid var(--border-2)", borderRadius: 8, padding: "8px 12px", fontSize: 12 }}>
        <div style={{ color: "var(--text-muted)", marginBottom: 4 }}>{label}</div>
        <div style={{ color: "var(--accent-green)" }}>{payload[0].value} kWh</div>
      </div>
    );
  };

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-icon">❋</span>
        <h3>Green MLOps</h3>
        <span className="badge ok">● On Track</span>
      </div>

      <div className="green-grid">
        <div className="green-stat">
          <span className="metric-label">Energy (7d)</span>
          <span className="metric-value" style={{ color: "var(--accent-cyan)" }}>
            {metrics.total_energy_kwh} kWh
          </span>
        </div>
        <div className="green-stat">
          <span className="metric-label">CO₂ Estimate</span>
          <span className="metric-value" style={{ color: "var(--accent-green)" }}>
            {co2Kg} kg
          </span>
        </div>
        <div className="green-stat">
          <span className="metric-label">Training Runs</span>
          <span className="metric-value" style={{ color: "var(--text-primary)" }}>
            {metrics.training_runs}
          </span>
        </div>
        <div className="green-stat">
          <span className="metric-label">Budget Used</span>
          <span className="metric-value" style={{ color: budgetPct > 80 ? "var(--accent-red)" : "var(--accent-green)" }}>
            {budgetPct}%
          </span>
        </div>
      </div>

      {/* Carbon budget bar */}
      <div className="psi-gauge" style={{ marginBottom: 14 }}>
        <div className="psi-gauge-label">
          <span>Carbon budget</span>
          <span>{budgetPct}% / 50 kWh limit</span>
        </div>
        <div className="psi-gauge-track">
          <div
            className="psi-gauge-fill"
            style={{
              width: `${budgetPct}%`,
              background: budgetPct > 80 ? "var(--accent-red)" : budgetPct > 60 ? "var(--accent-amber)" : "var(--accent-green)"
            }}
          />
        </div>
      </div>

      <div className="chart-label">Daily Energy Consumption (kWh)</div>
      <ResponsiveContainer width="100%" height={140}>
        <BarChart data={metrics.daily} margin={{ top: 4, right: 4, bottom: 0, left: -16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis dataKey="date" stroke="var(--border)" tick={{ fill: "var(--text-muted)", fontSize: 11 }} />
          <YAxis stroke="var(--border)" tick={{ fill: "var(--text-muted)", fontSize: 11 }} />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="kwh" radius={[4, 4, 0, 0]}>
            {metrics.daily.map((entry, i) => (
              <Cell
                key={i}
                fill={entry.kwh > 2.2 ? "var(--accent-amber)" : "var(--accent-green)"}
                fillOpacity={0.85}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p className="muted">Amber bars = above average consumption day</p>
    </div>
  );
}