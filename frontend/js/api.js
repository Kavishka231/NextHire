const BASE_URL = window.location.port === "5500"
  ? "/api/v1"
  : "http://localhost:8000/api/v1";

function getToken() {
  return localStorage.getItem("token");
}

async function request(endpoint, options = {}) {
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
