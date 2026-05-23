import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

const client = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

// ============================================================================
// EXISTING ENDPOINTS
// ============================================================================
export const getModelHealth = () => client.get("/models/health");
export const getDrift = () => client.get("/drift");
export const getGreenMetrics = (range = "7d") =>
  client.get(`/green-metrics?range=${range}`);

// ============================================================================
// NEW ANALYTICS ENDPOINTS
// ============================================================================

/**
 * Get KPI metrics (fraud prevention ROI, FPR reduction, annual ROI)
 * @returns {Promise} - KPI data with monthly trends
 */
export const getKPIMetrics = () => client.get("/analytics/kpi");

/**
 * Get live transaction feed with fraud predictions
 * @param {number} limit - Number of transactions to return (default: 20)
 * @returns {Promise} - Array of recent transactions with predictions
 */
export const getLiveTransactions = (limit = 20) => 
  client.get(`/analytics/transactions/live?limit=${limit}`);

/**
 * Get customer segmentation heatmap data (FPR/FNR by segment and region)
 * @returns {Promise} - Segmentation matrix with insights
 */
export const getCustomerSegmentation = () => 
  client.get("/analytics/segmentation");

/**
 * Get transaction volume and latency metrics over time
 * @param {number} hours - Number of hours to return data for (default: 24)
 * @returns {Promise} - Hourly volume and latency data
 */
export const getTransactionVolume = (hours = 24) => 
  client.get(`/analytics/volume?hours=${hours}`);

/**
 * Get confusion matrix data for model performance visualization
 * @returns {Promise} - Confusion matrix with derived metrics and cost analysis
 */
export const getConfusionMatrix = () => 
  client.get("/analytics/confusion-matrix");