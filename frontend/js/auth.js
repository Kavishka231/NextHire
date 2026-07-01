function showAlert(id, msg, type = "error") {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = msg;
  el.className = `alert ${type} visible`;
}

function hideAlert(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = "";
  el.className = "alert";
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
    window.location.replace("login.html");
    return false;
  }
  return true;
}

function setLoading(btn, loading) {
  if (!btn) return;
  if (loading) {
    btn.disabled = true;
    btn.dataset.originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner"></span> Please wait...';
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
  btn.textContent = show ? "Hide" : "Show";
  btn.setAttribute("aria-label", show ? "Hide password" : "Show password");
}

function redirectIfAuthed() {
  if (Auth.isLoggedIn()) {
    window.location.replace("dashboard.html");
  }
}

function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value || "").trim());
}

function isValidUrl(value) {
  if (!value) return true;
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol);
  } catch (_) {
    return false;
  }
}

function bindValidationClear(form) {
  form.querySelectorAll("input, textarea, select").forEach(field => {
    field.addEventListener("input", () => clearFieldError(field));
    field.addEventListener("change", () => clearFieldError(field));
  });
}

function clearFormErrors(form) {
  form.querySelectorAll(".error, .is-invalid").forEach(field => {
    field.classList.remove("error", "is-invalid");
    field.removeAttribute("aria-invalid");
  });
  form.querySelectorAll(".field-message").forEach(message => message.remove());
}

function clearFieldError(field) {
  field.classList.remove("error", "is-invalid");
  field.removeAttribute("aria-invalid");
  const id = field.id || field.name || "field";
  document.getElementById(`${id}-message`)?.remove();
}

function setFieldError(field, message) {
  if (!field) return false;
  const name = field.id || field.name || "field";
  const messageId = `${name}-message`;
  field.classList.add("error", "is-invalid");
  field.setAttribute("aria-invalid", "true");
  field.setAttribute("aria-describedby", messageId);

  let messageEl = document.getElementById(messageId);
  if (!messageEl) {
    messageEl = document.createElement("p");
    messageEl.id = messageId;
    messageEl.className = "field-message";
    const wrapper = field.closest(".password-field") || field;
    wrapper.insertAdjacentElement("afterend", messageEl);
  }
  messageEl.textContent = message;
  return false;
}

function requireField(field, message) {
  return field?.value?.trim() ? true : setFieldError(field, message);
}

function validateLoginForm(form) {
  clearFormErrors(form);
  let valid = true;
  if (!requireField(form.email, "Enter your email address.")) valid = false;
  else if (!isValidEmail(form.email.value)) valid = setFieldError(form.email, "Enter a valid email address.");
  if (!requireField(form.password, "Enter your password.")) valid = false;
  return valid;
}

function validateForgotForm(form) {
  clearFormErrors(form);
  if (!requireField(form.email, "Enter the email connected to your account.")) return false;
  return isValidEmail(form.email.value) || setFieldError(form.email, "Enter a valid email address.");
}

function validateRegisterForm(form) {
  clearFormErrors(form);
  let valid = true;
  if (!requireField(form.fullName, "Enter your full name.")) valid = false;
  if (!requireField(form.email, "Enter your email address.")) valid = false;
  else if (!isValidEmail(form.email.value)) valid = setFieldError(form.email, "Enter a valid email address.");
  if (!requireField(form.password, "Create a password.")) valid = false;
  else if (form.password.value.length < 8) valid = setFieldError(form.password, "Use at least 8 characters.");
  if (!requireField(form.confirmPassword, "Confirm your password.")) valid = false;
  else if (form.password.value !== form.confirmPassword.value) {
    valid = setFieldError(form.confirmPassword, "Passwords do not match.");
  }

  if (form.accountType.value === "company") {
    if (!requireField(form.companyName, "Enter your company name.")) valid = false;
    if (form.companyWebsite?.value?.trim() && !isValidUrl(form.companyWebsite.value.trim())) {
      valid = setFieldError(form.companyWebsite, "Use a full URL like https://company.com.");
    }
    if (!requireField(form.companyDescription, "Tell us what your company does.")) valid = false;
  }
  return valid;
}

function initPasswordToggles() {
  document.querySelectorAll(".toggle-password").forEach(btn => {
    btn.addEventListener("click", () => togglePasswordVisibility(btn.dataset.target, btn));
  });
}

function initLogin() {
  redirectIfAuthed();
  const form = document.getElementById("loginForm");
  if (!form) return;

  initPasswordToggles();
  bindValidationClear(form);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideAlert("alertBox");
    if (!validateLoginForm(form)) {
      showAlert("alertBox", "Check the highlighted fields and try again.");
      return;
    }

    const btn = form.querySelector("button[type=submit]");
    setLoading(btn, true);
    try {
      const data = await api.post("/auth/login", {
        email: form.email.value.trim(),
        password: form.password.value,
      });
      Auth.setTokens(data.access_token, data.refresh_token);
      window.location.href = "dashboard.html";
    } catch (err) {
      showAlert("alertBox", err.detail || "Login failed. Please try again.");
    } finally {
      setLoading(btn, false);
    }
  });
}

function initRegister() {
  redirectIfAuthed();
  const form = document.getElementById("registerForm");
  if (!form) return;

  initPasswordToggles();
  bindValidationClear(form);

  document.querySelectorAll('input[name="accountType"]').forEach(input => {
    input.addEventListener("change", () => {
      document.getElementById("companyFields")?.classList.toggle("hidden", input.value !== "company" || !input.checked);
      clearFormErrors(form);
    });
  });

  form.confirmPassword?.addEventListener("input", () => {
    const err = document.getElementById("confirmError");
    const mismatch = form.confirmPassword.value && form.confirmPassword.value !== form.password.value;
    form.confirmPassword.classList.toggle("error", mismatch);
    err?.classList.toggle("visible", mismatch);
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideAlert("alertBox");
    document.getElementById("confirmError")?.classList.remove("visible");
    if (!validateRegisterForm(form)) {
      showAlert("alertBox", "Check the highlighted fields and try again.");
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
      const next = new URLSearchParams(window.location.search).get("next") || "search.html?q=developer";
      setTimeout(() => { window.location.href = isCompany ? "login.html" : next; }, 1200);
    } catch (err) {
      showAlert("alertBox", err.detail || "Registration failed. Please try again.");
    } finally {
      setLoading(btn, false);
    }
  });
}

function initForgotPassword() {
  const form = document.getElementById("forgotForm");
  if (!form) return;
  bindValidationClear(form);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideAlert("alertBox");
    if (!validateForgotForm(form)) {
      showAlert("alertBox", "Enter a valid email address to continue.");
      return;
    }

    const btn = form.querySelector("button[type=submit]");
    setLoading(btn, true);
    try {
      await api.post("/auth/forgot-password", { email: form.email.value.trim() });
      showAlert("alertBox", "If that email is registered, a reset link is on its way.", "success");
    } catch (err) {
      showAlert("alertBox", err.detail || "Something went wrong.");
    } finally {
      setLoading(btn, false);
    }
  });
}

async function logout() {
  try {
    const refreshToken = Auth.getRefresh();
    if (refreshToken) {
      await api.post("/auth/logout", { refresh_token: refreshToken });
    }
  } catch (_) {
    /* best effort */
  }
  Auth.clearTokens();
  window.location.href = "login.html";
}
