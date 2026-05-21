import ModelHealth from "./components/ModelHealth";
import DriftMonitor from "./components/DriftMonitor";
import XAIExplainer from "./components/XAIExplainer";
import GreenMetrics from "./components/GreenMetrics";
import NLQueryInterface from "./components/NLQueryInterface";
import "./App.css";

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>IntelliPipeline</h1>
          <p>Intelligent MLOps — Secure & Green Banking AI</p>
        </div>
        <span className="tag">Fraud Detection · XAI · Auto-Retrain</span>
      </header>

      <main className="dashboard-grid">
        <section className="col-left">
          <ModelHealth />
          <DriftMonitor />
          <GreenMetrics />
          <XAIExplainer />
        </section>
        <section className="col-right">
          <NLQueryInterface />
        </section>
      </main>

      <footer className="app-footer">
        Apache Airflow · Azure Databricks · Delta Lake · Azure ML · MLflow · Claude API
      </footer>
    </div>
  );
}
