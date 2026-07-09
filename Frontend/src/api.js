const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "API request failed");
  }

  return response.json();
}

export const api = {
  getLatestRates: () => request("/rates/latest"),

  getLiveRates: () => request("/rates/live"),

  createAllSnapshots: () =>
    request("/rates/snapshot-all", {
      method: "POST",
    }),

  getHistory: (pair) =>
    request(`/rates/history/${encodeURIComponent(pair)}?limit=40`),

  getTreasurySummary: () => request("/treasury-summary"),

  getAlertRules: () => request("/alerts/rules"),

  getAlertEvents: () => request("/alerts/events"),

  createAlert: (payload) =>
    request("/alerts", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getExposures: () => request("/exposures"),

  createExposure: (payload) =>
    request("/exposures", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // "Why did it move?" explanation for a pair.
  getExplanation: (pair) =>
    request(`/explain/${encodeURIComponent(pair)}`),
};
