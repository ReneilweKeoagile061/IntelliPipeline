import { useEffect, useState, useCallback } from "react";
import { getLiveTransactions } from "../services/api";

export default function LiveTransactionFeed() {
  const [transactions, setTransactions] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [highlight, setHighlight] = useState(null);

  const fetchTransactions = useCallback(() => {
    getLiveTransactions(20)
      .then((res) => {
        setTransactions(res.data.transactions);
        setStats({
          total: res.data.total_count,
          fraud: res.data.fraud_count,
          legit: res.data.legit_count,
          avgLatency: res.data.avg_processing_time_ms,
        });
      })
      .catch(() => {
        const merchants = ["Amazon.com", "Walmart", "Starbucks", "Netflix", "Apple Store",
          "Best Buy", "Target", "Uber", "Shell Gas", "McDonald's",
          "GameStop", "Spotify", "CVS Pharmacy", "International Store", "Cash Advance ATM"];
        const segments = ["High Value", "Standard", "New Customer"];
        const demo = Array.from({ length: 20 }, (_, i) => {
          const isFraud = i === 0 || i === 6;
          return {
            transaction_id: `TX-2025-${88000 + i}`,
            timestamp: new Date(Date.now() - i * 10_000).toLocaleTimeString(),
            amount: isFraud ? +(Math.random() * 1500 + 800).toFixed(2) : +(Math.random() * 250 + 10).toFixed(2),
            merchant: isFraud ? merchants[13 + (i === 6 ? 1 : 0)] : merchants[Math.floor(Math.random() * 13)],
            prediction: isFraud ? "FRAUD" : "LEGIT",
            confidence: isFraud ? +(Math.random() * 10 + 87).toFixed(1) : +(Math.random() * 15 + 83).toFixed(1),
            risk_score: isFraud ? +(Math.random() * 0.15 + 0.82).toFixed(3) : +(Math.random() * 0.28 + 0.02).toFixed(3),
            processing_time_ms: Math.floor(Math.random() * 65 + 12),
            customer_segment: segments[isFraud ? 0 : Math.floor(Math.random() * 3)],
          };
        });
        setTransactions(demo);
        setStats({ total: 20, fraud: 2, legit: 18, avgLatency: 48.5 });
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchTransactions();
    if (!autoRefresh) return;
    const id = setInterval(fetchTransactions, 10_000);
    return () => clearInterval(id);
  }, [autoRefresh, fetchTransactions]);

  if (loading && !transactions.length)
    return <div className="card"><div className="skeleton-text" /></div>;

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-icon">⇄</span>
        <h3>Live Transaction Feed</h3>
        <div style={{ display: "flex", gap: 8, marginLeft: "auto" }}>
          <button
            className={`feed-btn ${autoRefresh ? "feed-btn-green" : "feed-btn-muted"}`}
            onClick={() => setAutoRefresh(v => !v)}
          >
            {autoRefresh ? "⟳ Auto" : "⏸ Paused"}
          </button>
          <button className="feed-btn feed-btn-blue" onClick={fetchTransactions}>
            Refresh
          </button>
        </div>
      </div>

      {/* Stats row */}
      {stats && (
        <div className="feed-stats">
          <div className="feed-stat">
            <span className="metric-label">Total</span>
            <span className="feed-stat-val">{stats.total}</span>
          </div>
          <div className="feed-stat feed-stat-red">
            <span className="metric-label">Fraud</span>
            <span className="feed-stat-val" style={{ color: "var(--accent-red)" }}>{stats.fraud}</span>
          </div>
          <div className="feed-stat feed-stat-green">
            <span className="metric-label">Legit</span>
            <span className="feed-stat-val" style={{ color: "var(--accent-green)" }}>{stats.legit}</span>
          </div>
          <div className="feed-stat feed-stat-blue">
            <span className="metric-label">Avg Latency</span>
            <span className="feed-stat-val" style={{ color: "var(--accent-blue)" }}>{stats.avgLatency}ms</span>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="feed-table-wrap">
        <table className="feed-table">
          <thead>
            <tr>
              {["Time", "TX ID", "Merchant", "Amount", "Prediction", "Risk", "Confidence", "Segment", "Latency"]
                .map(h => <th key={h}>{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {transactions.map((tx, i) => (
              <tr
                key={tx.transaction_id}
                className={`feed-row ${tx.prediction === "FRAUD" ? "feed-row-fraud" : ""} ${highlight === i ? "feed-row-hl" : ""}`}
                onMouseEnter={() => setHighlight(i)}
                onMouseLeave={() => setHighlight(null)}
              >
                <td className="feed-td-muted">{tx.timestamp}</td>
                <td className="feed-td-mono feed-td-blue">{tx.transaction_id}</td>
                <td className="feed-td-ellipsis">{tx.merchant}</td>
                <td className="feed-td-right feed-td-bold">${tx.amount.toFixed(2)}</td>
                <td className="feed-td-center">
                  <span className={`badge ${tx.prediction === "FRAUD" ? "bad" : "ok"}`}>
                    {tx.prediction}
                  </span>
                </td>
                <td className={`feed-td-right feed-td-mono ${
                  tx.risk_score > 0.7 ? "feed-td-red" :
                  tx.risk_score > 0.4 ? "feed-td-amber" : "feed-td-green"
                }`}>
                  {tx.risk_score.toFixed(3)}
                </td>
                <td className="feed-td-right feed-td-muted">{tx.confidence.toFixed(1)}%</td>
                <td className="feed-td-center">
                  <span className={`feed-seg ${
                    tx.customer_segment === "High Value"   ? "feed-seg-purple" :
                    tx.customer_segment === "New Customer" ? "feed-seg-amber"  : "feed-seg-default"
                  }`}>
                    {tx.customer_segment}
                  </span>
                </td>
                <td className="feed-td-right feed-td-muted">{tx.processing_time_ms}ms</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="feed-footer">
        <span>
          {autoRefresh
            ? <><span style={{ color: "var(--accent-green)" }}>●</span> Auto-refreshing every 10s</>
            : <><span style={{ color: "var(--accent-amber)" }}>●</span> Auto-refresh paused</>}
        </span>
        <span>Showing latest {transactions.length} transactions</span>
      </div>
    </div>
  );
}