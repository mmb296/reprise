const API_BASE_URL = "http://127.0.0.1:8000";

export const motifService = {
  // Motifs
  getMotifs: async (page, pageSize) => {
    const response = await fetch(
      `${API_BASE_URL}/motifs?page=${page}&page_size=${pageSize}`
    );
    return response.json();
  },

  createMotif: async (content, citation, autoGenerateClozeDeletions) => {
    const response = await fetch(`${API_BASE_URL}/motifs`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        content,
        citation,
        auto_generate_cloze_deletions: autoGenerateClozeDeletions,
      }),
    });
    return response.json();
  },

  updateMotif: async (uuid, content) => {
    const response = await fetch(`${API_BASE_URL}/motifs/${uuid}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ content }),
    });
    return response.json();
  },

  deleteMotif: async (uuid) => {
    const response = await fetch(`${API_BASE_URL}/motifs/${uuid}`, {
      method: "DELETE",
    });
    return response.json();
  },

  // Citations
  getCitations: async () => {
    const response = await fetch(`${API_BASE_URL}/citations`);
    return response.json();
  },

  // Cloze Deletions
  saveClozeDeletion: async (
    motifUuid,
    maskTuples,
    clozeDeletionUuid = null
  ) => {
    const payload = {
      mask_tuples: maskTuples,
      ...(clozeDeletionUuid
        ? { uuid: clozeDeletionUuid }
        : { motif_uuid: motifUuid }),
    };

    const response = await fetch(`${API_BASE_URL}/cloze_deletions`, {
      method: clozeDeletionUuid ? "PUT" : "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    return response.json();
  },

  deleteClozeDeletion: async (uuid) => {
    const response = await fetch(`${API_BASE_URL}/cloze_deletions/${uuid}`, {
      method: "DELETE",
    });
    return response.json();
  },
};
