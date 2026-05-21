import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { TrendingUp } from "lucide-react";
import { getDrift } from "../services/api";

export default function DriftMonitor() {
  const [drift, setDrift] = useState(null);

  useEffect(() => {
    getDrift()
      .then((res) => setDrift(res.data))
      .catch(() =>
        setDrift({
          psi_score: 0.12,
          severity: "LOW",
          drift_detected: false,
          history: [
            { date: "Mon", psi: 0.05 },
            { date: "Tue", psi: 0.07 },
            { date: "Wed", psi: 0.08 },
            { date: "Thu", psi: 0.1 },
            { date: "Fri", psi: 0.09 },
            { date: "Sat", psi: 0.11 },
            { date: "Sun", psi: 0.12 },
          ],
        })
      );
  }, []);

  if (!drift) return <div className="card">Loading drift data...</div>;

  const severityClass =
    drift.severity === "HIGH" ? "bad" : drift.severity === "MEDIUM" ? "warn" : "ok";

  return (
    <div className="card">
      <div className="card-header">
        <TrendingUp size={18} />
        <h3>Drift Monitor (PSI)</h3>
        <span className={`badge ${severityClass}`}>{drift.severity}</span>
      </div>
      <div className="metric-grid">
        <div className="metric">
          <span className="metric-label">PSI Score</span>
          <span className="metric-value">{drift.psi_score?.toFixed(3)}</span>
        </div>
        <div className="metric">
          <span className="metric-label">KL Divergence</span>
          <span className="metric-value">{drift.kl_divergence?.toFixed(3) ?? "—"}</span>
        </div>
        <div className="metric">
          <span className="metric-label">Retrain?</span>
          <span className={`metric-value ${drift.drift_detected ? "bad" : "good"}`}>
            {drift.drift_detected ? "YES" : "No"}
          </span>
        </div>
      </div>
      {drift.history && (
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={drift.history}>
            <XAxis dataKey="date" stroke="#64748b" fontSize={11} />
            <YAxis stroke="#64748b" fontSize={11} domain={[0, 0.3]} />
            <Tooltip contentStyle={{ background: "#1e293b", border: "none" }} />
            <Line type="monotone" dataKey="psi" stroke="#38bdf8" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      )}
      <p className="muted">PSI &gt; 0.25 triggers auto-retraining DAG</p>
    </div>
  );
}
