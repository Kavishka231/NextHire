const BASE_URL = window.NEXTHIRE_API_URL || "/api/v1";
let accessToken = null;
let refreshPromise = null;

function getToken() {
  return accessToken;
}

function setAccessToken(token) {
  accessToken = token || null;
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
    credentials: "include",
  });

  if (response.status === 401 && allowRefresh) {
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
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    try {
      const response = await fetch(`${BASE_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
      });

      if (!response.ok) {
        setAccessToken(null);
        return false;
      }
      const data = await response.json();
      setAccessToken(data.access_token);
      return Boolean(data.access_token);
    } catch (_) {
      setAccessToken(null);
      return false;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
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

function paginationQuery(page, pageSize = 25) {
  return `page=${encodeURIComponent(page)}&page_size=${encodeURIComponent(pageSize)}`;
}

function previousPageForEmptyResult(pageData) {
  return pageData.page > 1 && pageData.items.length === 0 ? pageData.page - 1 : null;
}

function renderCollectionPagination(anchorId, pageData, onPageChange) {
  const anchor = document.getElementById(anchorId);
  if (!anchor) return;

  const paginationId = `${anchorId}Pagination`;
  let root = document.getElementById(paginationId);
  const totalPages = Math.max(1, Math.ceil(pageData.total / pageData.page_size));
  if (totalPages <= 1) {
    root?.remove();
    return;
  }

  if (!root) {
    root = document.createElement("nav");
    root.id = paginationId;
    root.className = "pagination collection-pagination";
    root.setAttribute("aria-label", "Collection pagination");
    anchor.insertAdjacentElement("afterend", root);
  }

  root.innerHTML = `
    <button class="page-btn" type="button" data-page="${pageData.page - 1}" ${pageData.page <= 1 ? "disabled" : ""}>Previous</button>
    <span>Page ${pageData.page} of ${totalPages} <small>(${pageData.total} total)</small></span>
    <button class="page-btn" type="button" data-page="${pageData.page + 1}" ${pageData.page >= totalPages ? "disabled" : ""}>Next</button>
  `;
  root.querySelectorAll("button:not(:disabled)").forEach(button => {
    button.addEventListener("click", () => onPageChange(Number(button.dataset.page)));
  });
}
