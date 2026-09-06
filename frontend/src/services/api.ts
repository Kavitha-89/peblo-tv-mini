const API_BASE_URL = "http://127.0.0.1:8000";

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    try {
      const errorData = await response.json();

      if (typeof errorData.detail === "string") {
        message = errorData.detail;
      }
    } catch {
      // Keep the default error message.
    }

    throw new Error(message);
  }

  return response.json();
}

export async function getCatalogue<T>() {
  return apiRequest<T>("/catalog");
}

export async function searchCatalogue<T>(
  query: string,
  category?: string,
  language?: string,
  section?: string,
) {
  const params = new URLSearchParams();

  if (query) params.set("q", query);
  if (category) params.set("category", category);
  if (language) params.set("language", language);
  if (section) params.set("section", section);

  const queryString = params.toString();

  return apiRequest<T>(
    `/catalog/search${queryString ? `?${queryString}` : ""}`,
  );
}

export function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem("peblo_access_token");

  return token
    ? {
        Authorization: `Bearer ${token}`,
      }
    : {};
}