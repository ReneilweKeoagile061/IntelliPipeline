import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

const client = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

export const getModelHealth = () => client.get("/models/health");
export const getDrift = () => client.get("/drift");
export const getGreenMetrics = (range = "7d") =>
  client.get(`/green-metrics?range=${range}`);
