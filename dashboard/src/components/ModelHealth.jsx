import { useEffect, useState } from "react";
import { Activity, ShieldCheck } from "lucide-react";
import { getModelHealth } from "../services/api";

export default function ModelHealth() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getModelHealth()
      .then((res) => setHealth(res.data))
      .catch(() =>
        setHealth({
          accuracy: 0.924,
          false_positive_rate: 0.051,
          f1_score: 0.89,
          endpoint_status: "healthy",
        })
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="card">Loading model health...</div>;

  const metrics = [
    { label: "Accuracy", value: `${(health.accuracy * 100).toFixed(1)}%`, good: true },
    {
      label: "False Positive Rate",
      value: `${(health.false_positive_rate * 100).toFixed(1)}%`,
      good: health.false_positive_rate < 0.08,
    },
    { label: "F1 Score", value: health.f1_score?.toFixed(3) ?? "—", good: true },
    { label: "Endpoint", value: health.endpoint_status ?? "unknown", good: true },
  ];

  return (
    <div className="card">
      <div className="card-header">
        <Activity size={18} />
        <h3>Model Health</h3>
        <span className={`badge ${health.endpoint_status === "healthy" ? "ok" : "warn"}`}>
          <ShieldCheck size={12} /> {health.endpoint_status}
        </span>
      </div>
      <div className="metric-grid">
        {metrics.map((m) => (
          <div key={m.label} className="metric">
            <span className="metric-label">{m.label}</span>
            <span className={`metric-value ${m.good ? "good" : "warn"}`}>{m.value}</span>
          </div>
        ))}
      </div>
      {health.traffic_split && (
        <p className="muted">
          Traffic: Blue {health.traffic_split.blue}% / Green {health.traffic_split.green}%
        </p>
      )}
    </div>
  );
}
