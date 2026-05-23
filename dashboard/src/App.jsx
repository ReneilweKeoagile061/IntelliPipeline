import { useState } from "react";
import ModelHealth from "./components/ModelHealth";
import DriftMonitor from "./components/DriftMonitor";
import XAIExplainer from "./components/XAIExplainer";
import GreenMetrics from "./components/GreenMetrics";
import NLQueryInterface from "./components/NLQueryInterface";
import KPIMetrics from "./components/kpimetrics";
import LiveTransactionFeed from "./components/LiveTransactionFeed";
import CustomerSegmentation from "./components/CustomerSegmentation";
import "./App.css";

const NAV = [
  { section: "Main Menu" },
  { id: "overview",     icon: "⊞", label: "Overview" },
  { id: "transactions", icon: "⇄", label: "Transactions" },
  { id: "segments",     icon: "◑", label: "Segmentation" },
  { section: "ML Ops" },
  { id: "model",        icon: "◎", label: "Model Health" },
  { id: "drift",        icon: "∿", label: "Drift Monitor" },
  { id: "xai",          icon: "◈", label: "XAI Explainer" },
  { section: "Platform" },
  { id: "green",        icon: "❋", label: "Green MLOps" },
  { id: "query",        icon: "✦", label: "AI Query" },
];

export default function App() {
  const [active, setActive]       = useState("overview");
  const [sidebarOpen, setSidebar] = useState(true);

  const currentLabel = NAV.find(n => n.id === active)?.label ?? "Overview";

  return (
    <div className="shell">

      {/* ── Sidebar ─────────────────────────────────── */}
      <aside className={`sidebar ${sidebarOpen ? "open" : "closed"}`}>

        <div className="sidebar-brand">
          <div className="brand-icon">⬡</div>
          {sidebarOpen && (
            <div className="brand-text">
              <div className="brand-name">IntelliPipeline</div>
              <div className="brand-sub">MLOps Platform</div>
            </div>
          )}
        </div>

        <nav className="sidebar-nav">
          {NAV.map((item, i) =>
            item.section ? (
              sidebarOpen ? (
                <div key={i} className="nav-section">{item.section}</div>
              ) : (
                <div key={i} style={{ height: 10 }} />
              )
            ) : (
              <button
                key={item.id}
                className={`nav-item ${active === item.id ? "active" : ""}`}
                onClick={() => setActive(item.id)}
                title={!sidebarOpen ? item.label : undefined}
              >
                <span className="nav-icon">{item.icon}</span>
                {sidebarOpen && <span className="nav-label">{item.label}</span>}
                {active === item.id && <span className="nav-indicator" />}
              </button>
            )
          )}
        </nav>

        <div className="sidebar-footer">
          {sidebarOpen && (
            <div className="system-status">
              <span className="status-dot pulse" />
              <span className="status-text">All systems operational</span>
            </div>
          )}
          <button
            className="collapse-btn"
            onClick={() => setSidebar(v => !v)}
            title={sidebarOpen ? "Collapse" : "Expand"}
          >
            {sidebarOpen ? "◀" : "▶"}
          </button>
        </div>
      </aside>

      {/* ── Main ────────────────────────────────────── */}
      <div className="main-wrap">

        {/* Topbar */}
        <header className="topbar">
          <div className="topbar-left">
            <div className="page-title">{currentLabel}</div>
            <div className="page-breadcrumb">
              IntelliPipeline &rsaquo; {currentLabel}
            </div>
          </div>
          <div className="topbar-right">
            <div className="topbar-pill">
              <span className="dot green" /> Fraud Detection
            </div>
            <div className="topbar-pill">
              <span className="dot blue" /> XAI Active
            </div>
            <div className="topbar-pill">
              <span className="dot teal" /> Auto-Retrain
            </div>
            <div className="avatar">RK</div>
          </div>
        </header>

        {/* Pages */}
        <main className="content">

          {active === "overview" && (
            <div className="page-overview">
              <KPIMetrics />
              <div className="overview-grid">
                <div className="overview-col-left">
                  <ModelHealth />
                  <DriftMonitor />
                </div>
                <div className="overview-col-right">
                  <NLQueryInterface />
                </div>
              </div>
              <LiveTransactionFeed />
            </div>
          )}

          {active === "model"        && <div className="page-single"><ModelHealth /></div>}
          {active === "drift"        && <div className="page-single"><DriftMonitor /></div>}
          {active === "transactions" && (
            <div className="page-single">
              <LiveTransactionFeed />
            </div>
          )}
          {active === "segments"     && <div className="page-single"><CustomerSegmentation /></div>}
          {active === "xai"          && <div className="page-single"><XAIExplainer /></div>}
          {active === "green"        && <div className="page-single"><GreenMetrics /></div>}
          {active === "query"        && <div className="page-query"><NLQueryInterface /></div>}

        </main>

        <footer className="bottom-bar">
          <span>Apache Airflow</span><span className="sep">·</span>
          <span>Azure Databricks</span><span className="sep">·</span>
          <span>Delta Lake</span><span className="sep">·</span>
          <span>Azure ML</span><span className="sep">·</span>
          <span>MLflow</span><span className="sep">·</span>
          <span>Claude API</span>
        </footer>
      </div>
    </div>
  );
}