import { useState, useRef, useEffect } from "react";
import { queryIntelligence } from "../services/claudeService";

const EXAMPLES = [
  "What's the current model drift status?",
  "Show me the top fraud indicators from the XAI report",
  "What's our carbon footprint for training runs?",
  "Which model version should we roll back to?",
];

export default function NLQueryInterface() {
  const [messages, setMessages] = useState([{
    role: "assistant",
    content: "Hello! I'm IntelliPipeline's AI assistant. Ask me about model performance, drift, fraud patterns, or XAI explanations.\n\nTry: \"What's the current drift status?\"",
  }]);
  const [input,   setInput]   = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const send = async (text) => {
    const q = (text || input).trim();
    if (!q) return;
    const next = [...messages, { role: "user", content: q }];
    setMessages(next);
    setInput("");
    setLoading(true);
    try {
      const history = next.slice(1).map(m => ({ role: m.role, content: m.content }));
      const res = await queryIntelligence(q, history.slice(0, -1));
      setMessages(prev => [...prev, {
        role: "assistant",
        content: res.answer,
        metadata: { sources: res.context_sources, timestamp: res.timestamp },
      }]);
    } catch {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "Could not reach the API. Start the Flask backend: python api/app.py",
        error: true,
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="nl-query">
      <div className="nl-header">
        <h3>IntelliPipeline Intelligence Query</h3>
        <p>Claude API + RAG — Azure ML &amp; monitoring logs</p>
      </div>

      <div className="nl-messages">
        {messages.map((m, i) => (
          <div key={i} className={`nl-bubble ${m.role}`}>
            <div className={`nl-content ${m.error ? "error" : ""}`}>{m.content}</div>
            {m.metadata?.sources && (
              <div className="nl-meta">Sources: {m.metadata.sources.join(", ")}</div>
            )}
          </div>
        ))}
        {loading && (
          <div className="nl-bubble assistant">
            <div className="nl-content nl-typing">
              <span className="nl-dot" /><span className="nl-dot" /><span className="nl-dot" />
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {messages.length <= 1 && (
        <div className="nl-examples">
          {EXAMPLES.map((q, i) => (
            <button key={i} type="button" onClick={() => send(q)}>{q}</button>
          ))}
        </div>
      )}

      <div className="nl-input-row">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && !e.shiftKey && send()}
          placeholder="Ask about model performance, drift, fraud patterns..."
          disabled={loading}
        />
        <button type="button" onClick={() => send()} disabled={loading || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}