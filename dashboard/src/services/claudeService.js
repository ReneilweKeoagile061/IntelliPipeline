const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

async function parseJsonResponse(response, label) {
  if (!response.ok) {
    throw new Error(`${label} failed: ${response.status}`);
  }

  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    throw new Error(`${label} returned non-JSON response`);
  }

  return response.json();
}

export const queryIntelligence = async (question, conversationHistory = []) => {
  const response = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, conversation_history: conversationHistory }),
  });

  return parseJsonResponse(response, "Query");
};

export const getXAIExplanation = async (transactionId, audienceType = "executive") => {
  const response = await fetch(`${API_BASE}/explain/${transactionId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ audience: audienceType }),
  });

  return parseJsonResponse(response, "Explain");
};

export const getGreenMetrics = async (timeRange = "7d") => {
  const response = await fetch(`${API_BASE}/green-metrics?range=${timeRange}`);
  return parseJsonResponse(response, "Green metrics");
};
