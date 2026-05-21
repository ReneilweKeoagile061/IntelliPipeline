const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

export const queryIntelligence = async (question, conversationHistory = []) => {
  const response = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, conversation_history: conversationHistory }),
  });

  if (!response.ok) throw new Error(`Query failed: ${response.status}`);
  return response.json();
};

export const getXAIExplanation = async (transactionId, audienceType = "executive") => {
  const response = await fetch(`${API_BASE}/explain/${transactionId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ audience: audienceType }),
  });
  if (!response.ok) throw new Error(`Explain failed: ${response.status}`);
  return response.json();
};

export const getGreenMetrics = async (timeRange = "7d") => {
  const response = await fetch(`${API_BASE}/green-metrics?range=${timeRange}`);
  if (!response.ok) throw new Error(`Green metrics failed: ${response.status}`);
  return response.json();
};
