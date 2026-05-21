import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { Leaf } from "lucide-react";
import { getGreenMetrics } from "../services/claudeService";

export default function GreenMetrics() {
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    getGreenMetrics("7d")
      .then(setMetrics)
      .catch(() =>
        setMetrics({
          total_energy_kwh: 12.4,
          total_co2_grams: 5890,
          training_runs: 8,
          daily: [
            { date: "Mon", kwh: 1.8 },
            { date: "Tue", kwh: 2.1 },
            { date: "Wed", kwh: 1.5 },
            { date: "Thu", kwh: 2.4 },
            { date: "Fri", kwh: 1.9 },
            { date: "Sat", kwh: 1.2 },
            { date: "Sun", kwh: 1.5 },
          ],
        })
      );
  }, []);

  if (!metrics) return <div className="card">Loading green metrics...</div>;

  return (
    <div className="card">
      <div className="card-header">
        <Leaf size={18} />
        <h3>Green MLOps</h3>
      </div>
      <div className="metric-grid">
        <div className="metric">
          <span className="metric-label">Energy (7d)</span>
          <span className="metric-value">{metrics.total_energy_kwh} kWh</span>
        </div>
        <div className="metric">
          <span className="metric-label">CO₂ Estimate</span>
          <span className="metric-value">
            {(metrics.total_co2_grams / 1000).toFixed(1)} kg
          </span>
        </div>
        <div className="metric">
          <span className="metric-label">Training Runs</span>
          <span className="metric-value">{metrics.training_runs}</span>
        </div>
      </div>
      {metrics.daily && (
        <ResponsiveContainer width="100%" height={140}>
          <BarChart data={metrics.daily}>
            <XAxis dataKey="date" stroke="#64748b" fontSize={11} />
            <YAxis stroke="#64748b" fontSize={11} />
            <Tooltip contentStyle={{ background: "#1e293b", border: "none" }} />
            <Bar dataKey="kwh" fill="#4ade80" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
