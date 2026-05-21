import { useState, useRef, useEffect } from "react";
import { queryIntelligence } from "../services/claudeService";

export default function NLQueryInterface() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello! I'm IntelliPipeline's AI assistant. Ask me about model performance, drift, fraud patterns, or XAI explanations.\n\nTry: \"What's the current drift status?\"",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const EXAMPLE_QUERIES = [
    "What's the current model drift status?",
    "Show me the top fraud indicators from the XAI report",
    "What's our carbon footprint for training runs?",
    "Which model version should we roll back to?",
  ];

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (text) => {
    const question = text || input.trim();
    if (!question) return;

    const userMessage = { role: "user", content: question };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

    try {
      const history = newMessages
        .slice(1)
        .map((m) => ({ role: m.role, content: m.content }));

      const response = await queryIntelligence(question, history.slice(0, -1));

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.answer,
          metadata: {
            sources: response.context_sources,
            timestamp: response.timestamp,
          },
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Could not reach the API. Start the Flask backend: python api/app.py",
          error: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="nl-query">
      <div className="nl-header">
        <h3>IntelliPipeline Intelligence Query</h3>
        <p>Claude API + RAG — Azure ML & monitoring logs</p>
      </div>

      <div className="nl-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`nl-bubble ${msg.role}`}>
            <div className={`nl-content ${msg.error ? "error" : ""}`}>{msg.content}</div>
            {msg.metadata?.sources && (
              <div className="nl-meta">Sources: {msg.metadata.sources.join(", ")}</div>
            )}
          </div>
        ))}
        {loading && (
          <div className="nl-bubble assistant">
            <div className="nl-content muted">Querying platform context...</div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {messages.length <= 1 && (
        <div className="nl-examples">
          {EXAMPLE_QUERIES.map((q, i) => (
            <button key={i} type="button" onClick={() => sendMessage(q)}>
              {q}
            </button>
          ))}
        </div>
      )}

      <div className="nl-input-row">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
          placeholder="Ask about model performance, drift, fraud patterns..."
          disabled={loading}
        />
        <button type="button" onClick={() => sendMessage()} disabled={loading || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}
