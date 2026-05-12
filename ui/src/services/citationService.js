export const fetchCitations = async () => {
  const response = await fetch("http://127.0.0.1:8000/citations");
  if (!response.ok) {
    throw new Error("Failed to fetch citations");
  }
  return response.json();
};

export const addCitation = async (title) => {
  const response = await fetch("http://127.0.0.1:8000/citations", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ title }),
  });
  if (!response.ok) {
    throw new Error("Failed to add citation");
  }
  return response.json();
};
