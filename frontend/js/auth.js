// ── Shared UI helpers ─────────────────────────────────────────────────────────
function showAlert(id, msg, type = "error") {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = msg;
  el.className = `alert alert-${type} visible`;
}

function hideAlert(id) {
  const el = document.getElementById(id);
  if (el) el.className = "alert";
}

const Auth = {
  setTokens(accessToken, refreshToken) {
    if (accessToken) localStorage.setItem("token", accessToken);
    if (refreshToken) localStorage.setItem("refresh_token", refreshToken);
  },
  getToken() {
    return localStorage.getItem("token");
  },
  getRefresh() {
    return localStorage.getItem("refresh_token");
  },
  clearTokens() {
    localStorage.removeItem("token");
    localStorage.removeItem("refresh_token");
  },
  isLoggedIn() {
    return Boolean(localStorage.getItem("token"));
  },
};

function requireAuth() {
  if (!Auth.isLoggedIn()) {
    window.location.replace("/login.html");
    return false;
  }
  return true;
}

function setLoading(btn, loading) {
  if (loading) {
    btn.disabled = true;
    btn.dataset.originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner"></span> Please wait…';
  } else {
    btn.disabled = false;
    btn.innerHTML = btn.dataset.originalText || btn.innerHTML;
  }
}

function togglePasswordVisibility(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const show = input.type === "password";
  input.type = show ? "text" : "password";
  btn.innerHTML = show
    ? `<svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/></svg>`
    : `<svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>`;
}


// ════════════════════════════════════════════════════════════════════════════
//  LOGIN PAGE
// ════════════════════════════════════════════════════════════════════════════
function initLogin() {
  redirectIfAuthed();

  const form = document.getElementById("loginForm");
  if (!form) return;

  // Password toggle
  document.querySelectorAll(".toggle-password").forEach(btn => {
    btn.addEventListener("click", () => togglePasswordVisibility(btn.dataset.target, btn));
  });

  document.querySelectorAll('input[name="accountType"]').forEach(input => {
    input.addEventListener("change", () => {
      document.getElementById("companyFields")?.classList.toggle("hidden", input.value !== "company" || !input.checked);
    });
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideAlert("alertBox");
    const btn = form.querySelector("button[type=submit]");
    setLoading(btn, true);

    try {
      const data = await api.post("/auth/login", {
        email: form.email.value.trim(),
        password: form.password.value,
      });
      Auth.setTokens(data.access_token, data.refresh_token);
      window.location.href = "/dashboard.html";
    } catch (err) {
      showAlert("alertBox", err.detail || "Login failed. Please try again.");
    } finally {
      setLoading(btn, false);
    }
  });
}

function redirectIfAuthed() {
  if (Auth.isLoggedIn()) {
    window.location.replace("/dashboard.html");
  }
}
// ════════════════════════════════════════════════════════════════════════════
//  REGISTER PAGE
// ════════════════════════════════════════════════════════════════════════════
function initRegister() {
  redirectIfAuthed();

  const form = document.getElementById("registerForm");
  if (!form) return;

  document.querySelectorAll(".toggle-password").forEach(btn => {
    btn.addEventListener("click", () => togglePasswordVisibility(btn.dataset.target, btn));
  });

  // Live password confirmation check
  const confirmInput = document.getElementById("confirmPassword");
  if (confirmInput) {
    confirmInput.addEventListener("input", () => {
      const err = document.getElementById("confirmError");
      if (confirmInput.value && confirmInput.value !== form.password.value) {
        confirmInput.classList.add("error");
        if (err) err.classList.add("visible");
      } else {
        confirmInput.classList.remove("error");
        if (err) err.classList.remove("visible");
      }
    });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideAlert("alertBox");

    // Client-side validation. Some auth screens may not include confirmation.
    if (confirmInput && form.password.value !== confirmInput.value) {
      showAlert("alertBox", "Passwords do not match.");
      return;
    }

    const btn = form.querySelector("button[type=submit]");
    setLoading(btn, true);

    try {
      const isCompany = form.accountType.value === "company";
      await api.post("/auth/register", {
        email: form.email.value.trim(),
        full_name: form.fullName.value.trim(),
        password: form.password.value,
        account_type: form.accountType.value,
        company_name: form.companyName?.value.trim() || null,
        company_website: form.companyWebsite?.value.trim() || null,
        company_description: form.companyDescription?.value.trim() || null,
      });
      showAlert("alertBox",
        isCompany
          ? "Company request submitted. Admin approval is required before posting jobs."
          : "Account created! Taking you to job search.",
        "success"
      );
      form.reset();
      const next = new URLSearchParams(window.location.search).get("next") || "/search.html?q=developer";
      setTimeout(() => { window.location.href = isCompany ? "/login.html" : next; }, 1200);
    } catch (err) {
      showAlert("alertBox", err.detail || "Registration failed. Please try again.");
    } finally {
      setLoading(btn, false);
    }
  });
}


// ════════════════════════════════════════════════════════════════════════════
//  FORGOT PASSWORD PAGE
// ════════════════════════════════════════════════════════════════════════════
function initForgotPassword() {
  const form = document.getElementById("forgotForm");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideAlert("alertBox");
    const btn = form.querySelector("button[type=submit]");
    setLoading(btn, true);

    try {
      await api.post("/auth/forgot-password", { email: form.email.value.trim() });
      showAlert("alertBox",
        "If that email is registered, a reset link is on its way.",
        "success"
      );
    } catch (err) {
      showAlert("alertBox", err.detail || "Something went wrong.");
    } finally {
      setLoading(btn, false);
    }
  });
}


// ════════════════════════════════════════════════════════════════════════════
//  LOGOUT (callable from any page)
// ════════════════════════════════════════════════════════════════════════════
async function logout() {
  try {
    const refreshToken = Auth.getRefresh();
    if (refreshToken) {
      await api.post("/auth/logout", { refresh_token: refreshToken });
    }
  } catch (_) { /* best effort */ }
  Auth.clearTokens();
  window.location.href = "/login.html";
}
