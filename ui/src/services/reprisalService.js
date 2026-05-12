const API_BASE_URL = "http://127.0.0.1:8000";

export const reprisalService = {
  getReprisals: async () => {
    const response = await fetch(`${API_BASE_URL}/reprise`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error("Failed to fetch reprisals");
    }

    return response.json();
  },
};
