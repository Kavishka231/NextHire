const BASE_URL = window.location.port === "5500"
  ? "/api/v1"
  : "http://localhost:8000/api/v1";

function getToken() {
  return localStorage.getItem("token");
}

async function request(endpoint, options = {}) {
  return rawRequest(endpoint, options, true);
}

async function rawRequest(endpoint, options = {}, allowRefresh = true) {
  const token = getToken();

  const headers = {
    "Content-Type": "application/json",
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  };

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && allowRefresh && localStorage.getItem("refresh_token")) {
    const refreshed = await refreshAccessToken();
    if (refreshed) return rawRequest(endpoint, options, false);
  }

  if (!response.ok) {
    let error = {};
    try {
      error = await response.json();
    } catch (_) {
      error = { detail: "API Error" };
    }
    const detail = Array.isArray(error.detail)
      ? error.detail.map(item => item.msg).join(", ")
      : error.detail || "API Error";
    const err = new Error(detail);
    err.detail = detail;
    err.status = response.status;
    throw err;
  }

  if (response.status === 204) return null;
  return response.json();
}

async function refreshAccessToken() {
  try {
    const response = await fetch(`${BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: localStorage.getItem("refresh_token") }),
    });

    if (!response.ok) return false;
    const data = await response.json();
    if (data.access_token) localStorage.setItem("token", data.access_token);
    if (data.refresh_token) localStorage.setItem("refresh_token", data.refresh_token);
    return Boolean(data.access_token);
  } catch (_) {
    return false;
  }
}

const api = {
  get(endpoint, options = {}) {
    return request(endpoint, { ...options, method: "GET" });
  },
  post(endpoint, body = {}, options = {}) {
    return request(endpoint, { ...options, method: "POST", body: JSON.stringify(body) });
  },
  put(endpoint, body = {}, options = {}) {
    return request(endpoint, { ...options, method: "PUT", body: JSON.stringify(body) });
  },
  patch(endpoint, body = {}, options = {}) {
    return request(endpoint, { ...options, method: "PATCH", body: JSON.stringify(body) });
  },
  delete(endpoint, options = {}) {
    return request(endpoint, { ...options, method: "DELETE" });
  },
};
