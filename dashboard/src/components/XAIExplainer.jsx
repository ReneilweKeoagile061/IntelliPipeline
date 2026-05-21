import { useState } from "react";
import { Brain } from "lucide-react";
import { getXAIExplanation } from "../services/claudeService";

export default function XAIExplainer() {
  const [txId, setTxId] = useState("TX-2025-88421");
  const [audience, setAudience] = useState("executive");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const explain = async () => {
    setLoading(true);
    try {
      const data = await getXAIExplanation(txId, audience);
      setResult(data);
    } catch {
      setResult({
        explanation: "Could not reach explain API. Ensure Flask backend is running.",
        error: true,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <Brain size={18} />
        <h3>XAI Explainer (SHAP + Claude)</h3>
      </div>
      <div className="xai-controls">
        <input
          value={txId}
          onChange={(e) => setTxId(e.target.value)}
          placeholder="Transaction ID"
        />
        <select value={audience} onChange={(e) => setAudience(e.target.value)}>
          <option value="executive">Executive</option>
          <option value="analyst">Risk Analyst</option>
        </select>
        <button onClick={explain} disabled={loading}>
          {loading ? "Explaining..." : "Explain"}
        </button>
      </div>
      {result && (
        <div className={`xai-result ${result.error ? "error" : ""}`}>
          <p>{result.explanation}</p>
          {result.shap_factors && (
            <ul>
              {result.shap_factors.map((f, i) => (
                <li key={i}>
                  <strong>{f.feature}</strong> (SHAP {f.shap_value?.toFixed?.(2) ?? f.shap_value})
                  — {f.description}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
