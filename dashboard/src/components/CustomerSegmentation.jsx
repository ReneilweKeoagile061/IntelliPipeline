import { useEffect, useState } from "react";
import { getCustomerSegmentation } from "../services/api";

const FALLBACK = {
  segmentation: [
    { segment: "High Value",
      Domestic:      { fpr: 0.32, fnr: 3.57, transaction_count: 12000, false_positives: 38, fraud_detected: 68 },
      International: { fpr: 0.47, fnr: 2.38, transaction_count:  3600, false_positives: 17, fraud_detected: 24 },
      "Cross-Border":{ fpr: 0.63, fnr: 1.79, transaction_count:  2400, false_positives: 15, fraud_detected: 18 } },
    { segment: "Mid Value",
      Domestic:      { fpr: 0.45, fnr: 2.50, transaction_count:  8000, false_positives: 36, fraud_detected: 45 },
      International: { fpr: 0.68, fnr: 1.67, transaction_count:  2400, false_positives: 16, fraud_detected: 16 },
      "Cross-Border":{ fpr: 0.90, fnr: 1.25, transaction_count:  1600, false_positives: 14, fraud_detected: 13 } },
    { segment: "Low Value",
      Domestic:      { fpr: 0.45, fnr: 2.50, transaction_count:  7000, false_positives: 32, fraud_detected: 39 },
      International: { fpr: 0.68, fnr: 1.67, transaction_count:  2100, false_positives: 14, fraud_detected: 14 },
      "Cross-Border":{ fpr: 0.90, fnr: 1.25, transaction_count:  1400, false_positives: 13, fraud_detected: 11 } },
    { segment: "New Customer",
      Domestic:      { fpr: 0.81, fnr: 1.39, transaction_count:  2000, false_positives: 16, fraud_detected: 11 },
      International: { fpr: 1.22, fnr: 0.93, transaction_count:   600, false_positives:  7, fraud_detected:  4 },
      "Cross-Border":{ fpr: 1.62, fnr: 0.69, transaction_count:   400, false_positives:  6, fraud_detected:  3 } },
  ],
  regions: ["Domestic", "International", "Cross-Border"],
  overall_stats: { total_transactions: 46500, average_fpr: 0.73,
    highest_fpr_segment: "New Customer - Cross-Border", lowest_fpr_segment: "High Value - Domestic" },
  insights: [
    { type: "warning",        message: "International transactions have 2× higher FPR than domestic" },
    { type: "info",           message: "High-value customers get stricter review to minimise friction" },
    { type: "recommendation", message: "Consider separate models for cross-border vs domestic transactions" },
  ],
};

const cellColor = (value, metric) => {
  if (metric === "fpr") {
    if (value < 0.40) return { bg: "rgba(16,185,129,0.12)", border: "rgba(16,185,129,0.3)", text: "#34d399" };
    if (value < 0.70) return { bg: "rgba(245,158,11,0.12)", border: "rgba(245,158,11,0.3)", text: "#fbbf24" };
    if (value < 1.00) return { bg: "rgba(249,115,22,0.12)", border: "rgba(249,115,22,0.3)", text: "#fb923c" };
    return                    { bg: "rgba(239,68,68,0.12)",  border: "rgba(239,68,68,0.3)",  text: "#f87171" };
  }
  if (value > 3.0)  return { bg: "rgba(16,185,129,0.12)",  border: "rgba(16,185,129,0.3)",  text: "#34d399" };
  if (value > 2.0)  return { bg: "rgba(245,158,11,0.12)",  border: "rgba(245,158,11,0.3)",  text: "#fbbf24" };
  if (value > 1.5)  return { bg: "rgba(249,115,22,0.12)",  border: "rgba(249,115,22,0.3)",  text: "#fb923c" };
  return                    { bg: "rgba(239,68,68,0.12)",   border: "rgba(239,68,68,0.3)",   text: "#f87171" };
};

const insightStyle = (type) => ({
  warning:        { bg: "rgba(245,158,11,0.08)",  border: "rgba(245,158,11,0.25)",  icon: "⚠", color: "#fbbf24" },
  info:           { bg: "rgba(59,130,246,0.08)",  border: "rgba(59,130,246,0.25)",  icon: "ℹ", color: "#60a5fa" },
  recommendation: { bg: "rgba(139,92,246,0.08)", border: "rgba(139,92,246,0.25)", icon: "💡", color: "#a78bfa" },
}[type] ?? { bg: "var(--bg-2)", border: "var(--border)", icon: "·", color: "var(--text-muted)" });

export default function CustomerSegmentation() {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [metric, setMetric]   = useState("fpr");

  useEffect(() => {
    getCustomerSegmentation()
      .then(res => setData(res.data))
      .catch(() => setData(FALLBACK))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="card"><div className="skeleton-text" /></div>;

  const { segmentation, regions, overall_stats, insights } = data;

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-icon">◑</span>
        <h3>Customer Segmentation Performance</h3>
        <div className="seg-toggle">
          {["fpr", "fnr"].map(m => (
            <button
              key={m}
              className={`seg-toggle-btn ${metric === m ? "active" : ""}`}
              onClick={() => setMetric(m)}
            >
              {m === "fpr" ? "FPR (False Positive)" : "FNR (False Negative)"}
            </button>
          ))}
        </div>
      </div>

      {/* Overview stats */}
      <div className="seg-stats">
        <div className="seg-stat">
          <span className="metric-label">Total Transactions</span>
          <span style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)" }}>
            {overall_stats.total_transactions.toLocaleString()}
          </span>
        </div>
        <div className="seg-stat">
          <span className="metric-label">Avg FPR</span>
          <span style={{ fontSize: 20, fontWeight: 700, color: "var(--accent-blue)" }}>
            {overall_stats.average_fpr.toFixed(2)}%
          </span>
        </div>
        <div className="seg-stat seg-stat-green">
          <span className="metric-label">Best Segment</span>
          <span style={{ fontSize: 13, fontWeight: 600, color: "var(--accent-green)" }}>
            {overall_stats.lowest_fpr_segment}
          </span>
        </div>
        <div className="seg-stat seg-stat-red">
          <span className="metric-label">Highest Risk</span>
          <span style={{ fontSize: 13, fontWeight: 600, color: "var(--accent-red)" }}>
            {overall_stats.highest_fpr_segment}
          </span>
        </div>
      </div>

      {/* Heatmap table */}
      <div className="seg-table-wrap">
        <table className="seg-table">
          <thead>
            <tr>
              <th>Segment</th>
              {regions.map(r => <th key={r}>{r}</th>)}
            </tr>
          </thead>
          <tbody>
            {segmentation.map(row => (
              <tr key={row.segment}>
                <td className="seg-segment-name">{row.segment}</td>
                {regions.map(region => {
                  const cell = row[region];
                  const val  = cell[metric];
                  const c    = cellColor(val, metric);
                  return (
                    <td key={region} style={{ background: c.bg, border: `1px solid ${c.border}` }} className="seg-cell">
                      <span style={{ fontSize: 18, fontWeight: 700, color: c.text, display: "block" }}>
                        {val.toFixed(2)}%
                      </span>
                      <span className="seg-cell-sub">{cell.transaction_count.toLocaleString()} txns</span>
                      <span className="seg-cell-sub" style={{ color: "var(--text-muted)" }}>
                        {metric === "fpr" ? `${cell.false_positives} FP` : `${cell.fraud_detected} detected`}
                      </span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="seg-legend">
        {[
          { label: metric === "fpr" ? "Low (<0.4%)" : "Conservative (>3%)", bg: "rgba(16,185,129,0.2)", border: "rgba(16,185,129,0.5)" },
          { label: metric === "fpr" ? "Medium (0.4–0.7%)" : "Moderate (2–3%)", bg: "rgba(245,158,11,0.2)", border: "rgba(245,158,11,0.5)" },
          { label: metric === "fpr" ? "High (0.7–1%)" : "Aggressive (1.5–2%)", bg: "rgba(249,115,22,0.2)", border: "rgba(249,115,22,0.5)" },
          { label: metric === "fpr" ? "Very High (>1%)" : "Very Aggressive (<1.5%)", bg: "rgba(239,68,68,0.2)", border: "rgba(239,68,68,0.5)" },
        ].map(l => (
          <div key={l.label} className="seg-legend-item">
            <div style={{ width: 14, height: 14, background: l.bg, border: `1px solid ${l.border}`, borderRadius: 3, flexShrink: 0 }} />
            <span>{l.label}</span>
          </div>
        ))}
      </div>

      {/* Insights */}
      <div className="seg-insights">
        <span className="metric-label" style={{ marginBottom: 8, display: "block" }}>Key Insights</span>
        {insights.map((ins, i) => {
          const s = insightStyle(ins.type);
          return (
            <div key={i} className="seg-insight" style={{ background: s.bg, borderColor: s.border }}>
              <span style={{ color: s.color, fontSize: 13 }}>{s.icon}</span>
              <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{ins.message}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}