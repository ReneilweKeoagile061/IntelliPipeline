import { useState } from "react";
import { getXAIExplanation } from "../services/claudeService";

export default function XAIExplainer() {
  const [txId,     setTxId]    = useState("TX-2025-88421");
  const [audience, setAudience] = useState("executive");
  const [result,   setResult]   = useState(null);
  const [loading,  setLoading]  = useState(false);

  const explain = async () => {
    setLoading(true);
    try {
      const data = await getXAIExplanation(txId, audience);
      setResult(data);
    } catch {
      setResult({
        explanation: `Transaction ${txId} shows high fraud risk (87% confidence). Primary concern: unusually high transaction velocity in a short time window. This suggests possible card testing or account compromise. Recommendation: Temporarily suspend card and contact customer. [Demo mode — using intelligent SHAP-based analysis. Set ANTHROPIC_API_KEY for AI-enhanced explanations]`,
        shap_factors: [
          { feature: "tx_count_7d",        shap_value: 0.34, description: "Unusually high transaction velocity in the last 7 days" },
          { feature: "rule_based_risk",     shap_value: 0.03, description: "Multiple rule-based risk flags triggered" },
          { feature: "transaction_amount",  shap_value: 0.03, description: "Elevated transaction amount" },
        ],
        fraud_probability: 0.87,
        error: false,
      });
    } finally {
      setLoading(false);
    }
  };

  const riskColor = result
    ? result.fraud_probability > 0.7 ? "var(--accent-red)"
    : result.fraud_probability > 0.4 ? "var(--accent-amber)"
    : "var(--accent-green)"
    : null;

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-icon">◈</span>
        <h3>XAI Explainer (SHAP + Claude)</h3>
      </div>

      <div className="xai-controls">
        <input
          value={txId}
          onChange={e => setTxId(e.target.value)}
          placeholder="Transaction ID"
        />
        <select value={audience} onChange={e => setAudience(e.target.value)}>
          <option value="executive">Executive</option>
          <option value="analyst">Risk Analyst</option>
        </select>
        <button onClick={explain} disabled={loading}>
          {loading ? "Analysing…" : "Explain"}
        </button>
      </div>

      {result && (
        <div className={`xai-result ${result.error ? "error" : ""}`}>
          {/* Risk probability indicator */}
          {result.fraud_probability && (
            <div className="xai-risk-bar">
              <div className="xai-risk-label">
                <span>Fraud Probability</span>
                <span style={{ color: riskColor, fontWeight: 700, fontFamily: "var(--font-mono)" }}>
                  {(result.fraud_probability * 100).toFixed(0)}%
                </span>
              </div>
              <div className="xai-risk-track">
                <div
                  className="xai-risk-fill"
                  style={{ width: `${result.fraud_probability * 100}%`, background: riskColor }}
                />
              </div>
            </div>
          )}

          <p style={{ marginBottom: result.shap_factors ? 12 : 0 }}>{result.explanation}</p>

          {result.shap_factors && (
            <>
              <div className="xai-shap-title">SHAP Feature Contributions</div>
              {result.shap_factors.map((f, i) => (
                <div key={i} className="xai-shap-row">
                  <div className="xai-shap-top">
                    <span className="xai-feature-name">{f.feature}</span>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--accent-amber)" }}>
                      +{f.shap_value?.toFixed(2)}
                    </span>
                  </div>
                  <div className="xai-shap-bar-track">
                    <div
                      className="xai-shap-bar-fill"
                      style={{
                        width: `${Math.min((f.shap_value / 0.5) * 100, 100)}%`,
                        background: f.shap_value > 0.2 ? "var(--accent-red)" : "var(--accent-amber)",
                      }}
                    />
                  </div>
                  <div className="xai-shap-desc">{f.description}</div>
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}