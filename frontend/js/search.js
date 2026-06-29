// ── State ─────────────────────────────────────────────────────────────────────
let state = {
  keywords: "",
  location: "",
  page: 1,
  perPage: 20,
  salaryMin: null,
  salaryMax: null,
  fullTime: null,
  sortBy: "relevance",
  country: "gb",
  total: 0,
  jobs: [],
  loading: false,
  activeJob: null,
};


// ── Init ──────────────────────────────────────────────────────────────────────
async function initSearch() {
  setupPublicNav();
  if (Auth.isLoggedIn()) loadUserInfo();

  // Restore query from URL params
  const params = new URLSearchParams(window.location.search);
  if (params.get("q")) {
    state.keywords = params.get("q");
    document.getElementById("searchKeywords").value = state.keywords;
  }
  if (params.get("location")) {
    state.location = params.get("location");
    document.getElementById("searchLocation").value = state.location;
    document.getElementById("filterLocation").value = state.location;
  }

  bindEvents();
  loadCategories();

  if (state.keywords) await runSearch();
}


// ── Load current user info for nav ────────────────────────────────────────────
async function loadUserInfo() {
  try {
    const user = await api.get("/auth/me");
    const initials = user.full_name.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2);
    const el = document.getElementById("navInitials");
    if (el) el.textContent = initials;
    const name = document.getElementById("navUserName");
    if (name) name.textContent = user.full_name;
    const email = document.getElementById("navUserEmail");
    if (email) email.textContent = user.email;
  } catch (_) { }
}


// ── Event binding ─────────────────────────────────────────────────────────────
function bindEvents() {
  // Hero search form
  document.getElementById("heroSearchForm")?.addEventListener("submit", (e) => {
    e.preventDefault();
    state.keywords = document.getElementById("searchKeywords").value.trim();
    state.location = document.getElementById("searchLocation").value.trim();
    state.page = 1;
    runSearch();
  });

  // Sort select
  document.getElementById("sortSelect")?.addEventListener("change", (e) => {
    state.sortBy = e.target.value;
    state.page = 1;
    runSearch();
  });

  // Filter apply
  document.getElementById("applyFilters")?.addEventListener("click", applyFilters);

  // Filter reset
  document.getElementById("resetFilters")?.addEventListener("click", resetFilters);

  // Quick chips
  document.querySelectorAll(".search-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".search-chip").forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      const kw = chip.dataset.kw;
      if (kw === "all") { state.keywords = document.getElementById("searchKeywords").value.trim() || "developer"; }
      else { state.keywords = kw; document.getElementById("searchKeywords").value = kw; }
      state.page = 1;
      runSearch();
    });
  });

  document.querySelectorAll(".starter-card").forEach(card => {
    card.addEventListener("click", () => {
      state.keywords = card.dataset.starter || "developer";
      state.location = card.dataset.location || "";
      state.page = 1;
      document.getElementById("searchKeywords").value = state.keywords;
      document.getElementById("searchLocation").value = state.location;
      document.getElementById("filterLocation").value = state.location;
      runSearch();
    });
  });

  // Drawer overlay click closes drawer
  document.getElementById("drawerOverlay")?.addEventListener("click", closeDrawer);
  document.getElementById("drawerClose")?.addEventListener("click", closeDrawer);

  // Keyboard ESC closes drawer
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });

  // Mobile filter toggle
  document.getElementById("mobileFilterBtn")?.addEventListener("click", () => {
    document.querySelector(".search-filters-panel")?.classList.toggle("open");
  });

  // Avatar menu
  document.getElementById("navAvatar")?.addEventListener("click", (e) => {
    e.stopPropagation();
    document.getElementById("avatarMenu")?.classList.toggle("open");
  });

  document.addEventListener("click", () => {
    document.getElementById("avatarMenu")?.classList.remove("open");
  });
}


// ── Load job categories into filter dropdown ───────────────────────────────────
async function loadCategories() {
  try {
    const cats = await api.get(`/search/categories?country=${state.country}`);
    const select = document.getElementById("filterCategory");
    if (!select) return;
    cats.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.tag;
      opt.textContent = c.label;
      select.appendChild(opt);
    });
  } catch (_) { }
}


// ── Apply sidebar filters ──────────────────────────────────────────────────────
function applyFilters() {
  state.salaryMin = parseInt(document.getElementById("filterSalaryMin")?.value) || null;
  state.salaryMax = parseInt(document.getElementById("filterSalaryMax")?.value) || null;
  state.location = document.getElementById("filterLocation")?.value.trim() || "";
  document.getElementById("searchLocation").value = state.location;

  const ft = document.querySelector('input[name="contractTime"]:checked')?.value;
  state.fullTime = ft === "full" ? true
    : ft === "part" ? false
      : null;

  state.page = 1;
  runSearch();

  // Close mobile panel
  document.querySelector(".search-filters-panel")?.classList.remove("open");
}


function resetFilters() {
  state.salaryMin = null;
  state.salaryMax = null;
  state.fullTime = null;
  document.getElementById("filterSalaryMin").value = "";
  document.getElementById("filterSalaryMax").value = "";
  document.getElementById("filterLocation").value = "";
  document.querySelectorAll('input[name="contractTime"]').forEach(r => r.checked = false);
  document.querySelector('input[name="contractTime"][value="any"]').checked = true;
  state.page = 1;
  runSearch();
}


// ── Core search ───────────────────────────────────────────────────────────────
async function runSearch() {
  if (state.loading) return;
  state.loading = true;

  // Update URL without reload
  const urlParams = new URLSearchParams();
  if (state.keywords) urlParams.set("q", state.keywords);
  if (state.location) urlParams.set("location", state.location);
  window.history.replaceState({}, "", `?${urlParams}`);

  showSkeletons();
  updateResultsHeader(null);

  try {
    const params = new URLSearchParams({
      keywords: state.keywords || "developer",
      location: state.location,
      page: state.page,
      results_per_page: state.perPage,
      sort_by: state.sortBy,
      country: state.country,
    });
    if (state.salaryMin) params.set("salary_min", state.salaryMin);
    if (state.salaryMax) params.set("salary_max", state.salaryMax);
    if (state.fullTime !== null) params.set("full_time", state.fullTime);

    const data = await api.get(`/search/jobs?${params}`);
    state.jobs = data.jobs;
    state.total = data.total;

    renderJobs(data.jobs);
    updateResultsHeader(data.total);
    renderPagination(data.total);
  } catch (err) {
    renderError(err.detail || "Search failed. Please try again.");
  } finally {
    state.loading = false;
  }
}


// ── Render jobs ───────────────────────────────────────────────────────────────
function renderJobs(jobs) {
  const container = document.getElementById("jobsList");
  if (!container) return;

  if (!jobs.length) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">
          <svg width="28" height="28" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round"
              d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 15.803 7.5 7.5 0 0015.803 15.803z"/>
          </svg>
        </div>
        <h3>No jobs found</h3>
        <p>Try different keywords, a broader location, or remove some filters.</p>
      </div>`;
    return;
  }

  container.innerHTML = jobs.map((job, idx) => jobCardHTML(job, idx)).join("");

  // Bind card clicks
  container.querySelectorAll(".job-card").forEach((card, idx) => {
    card.addEventListener("click", (e) => {
      if (e.target.closest(".job-card-save")) return;
      window.location.href = `/job-detail.html?external_id=${encodeURIComponent(jobs[idx].external_id)}`;
    });
  });

  // Bind save buttons
  container.querySelectorAll(".job-card-save").forEach((btn, idx) => {
    btn.addEventListener("click", () => handleSave(jobs[idx], btn));
  });
}


function jobCardHTML(job, idx) {
  const initials = (job.company || "?").slice(0, 2).toUpperCase();
  const salary = formatSalary(job.salary_min, job.salary_max, job.salary_is_predicted);
  const location = job.location || "Location not specified";
  const contractBadge = job.contract_time === "full_time"
    ? `<span class="badge badge-blue">Full-time</span>`
    : job.contract_time === "part_time"
      ? `<span class="badge badge-amber">Part-time</span>`
      : "";
  const timeAgo = formatDate(job.created);

  return `
    <div class="job-card" data-idx="${idx}">
      <div class="job-card-header">
        <div class="job-company-logo">${initials}</div>
        <div class="job-card-titles">
          <div class="job-title">${escHtml(job.title)}</div>
          <div class="job-company">
            <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0H5"/>
            </svg>
            ${escHtml(job.company || "Company not listed")} ${job.company_verified ? `<span class="verified-badge">Verified</span>` : ""}
          </div>
        </div>
        <button class="job-card-save" data-id="${escHtml(job.external_id)}" title="Save job">
          <svg width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"/>
          </svg>
          Save
        </button>
      </div>

      <div class="job-meta">
        <span class="job-meta-item">
          <svg width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
          </svg>
          ${escHtml(location)}
        </span>
        ${salary ? `<span class="job-meta-item">
          <svg width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1"/>
          </svg>
          ${salary}
        </span>` : ""}
        ${timeAgo ? `<span class="job-meta-item">
          <svg width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          ${timeAgo}
        </span>` : ""}
      </div>

      <p class="job-description">${escHtml(stripHtml(job.description || ""))}</p>

      <div class="job-card-footer">
        <div class="job-tags">
          ${job.source === "company" ? `<span class="badge badge-blue">Direct post</span>` : ""}
          ${contractBadge}
          ${job.category ? `<span class="tag">${escHtml(job.category)}</span>` : ""}
        </div>
        ${salary ? `<span class="job-salary">${salary}</span>` : ""}
      </div>
    </div>`;
}


function showSkeletons() {
  const container = document.getElementById("jobsList");
  if (!container) return;
  container.innerHTML = Array.from({ length: 5 }).map(() => `
    <div class="job-card job-card-skeleton">
      <div class="job-card-header">
        <div class="skel-logo skeleton"></div>
        <div style="flex:1">
          <div class="skel-title skeleton"></div>
          <div class="skel-sub skeleton"></div>
        </div>
      </div>
      <div class="skel-meta skeleton"></div>
      <div class="skel-desc skeleton"></div>
      <div class="skel-desc2 skeleton"></div>
    </div>`).join("");
}


function renderError(msg) {
  const container = document.getElementById("jobsList");
  if (!container) return;
  container.innerHTML = `
    <div class="empty-state">
      <div class="empty-state-icon" style="background:var(--red-50)">
        <svg width="28" height="28" fill="none" viewBox="0 0 24 24" stroke="var(--red-500)" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/>
        </svg>
      </div>
      <h3>Something went wrong</h3>
      <p>${escHtml(msg)}</p>
    </div>`;
}


// ── Results header ────────────────────────────────────────────────────────────
function updateResultsHeader(total) {
  const el = document.getElementById("resultsCount");
  if (!el) return;
  if (total === null) {
    el.innerHTML = `<span class="skeleton" style="width:160px;height:14px;display:inline-block"></span>`;
  } else {
    const kw = state.keywords ? `"${escHtml(state.keywords)}"` : "all jobs";
    el.innerHTML = `<strong>${total.toLocaleString()}</strong> results for ${kw}`;
  }
}


// ── Pagination ────────────────────────────────────────────────────────────────
function renderPagination(total) {
  const container = document.getElementById("pagination");
  if (!container) return;

  const totalPages = Math.ceil(total / state.perPage);
  if (totalPages <= 1) { container.innerHTML = ""; return; }

  let html = `
    <button class="page-btn" onclick="goPage(${state.page - 1})" ${state.page === 1 ? "disabled" : ""}>
      <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
      </svg>
    </button>`;

  const range = pageRange(state.page, totalPages);
  range.forEach(p => {
    if (p === "…") {
      html += `<span style="padding:0 4px;color:var(--slate-400)">…</span>`;
    } else {
      html += `<button class="page-btn ${p === state.page ? "active" : ""}" onclick="goPage(${p})">${p}</button>`;
    }
  });

  html += `
    <button class="page-btn" onclick="goPage(${state.page + 1})" ${state.page === totalPages ? "disabled" : ""}>
      <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
      </svg>
    </button>`;

  container.innerHTML = html;
}

function pageRange(current, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  if (current <= 4) return [1, 2, 3, 4, 5, "…", total];
  if (current >= total - 3) return [1, "…", total - 4, total - 3, total - 2, total - 1, total];
  return [1, "…", current - 1, current, current + 1, "…", total];
}

function goPage(p) {
  state.page = p;
  runSearch();
  window.scrollTo({ top: 0, behavior: "smooth" });
}


// ── Job drawer ────────────────────────────────────────────────────────────────
function openDrawer(job) {
  state.activeJob = job;
  const drawer = document.getElementById("jobDrawer");
  const overlay = document.getElementById("drawerOverlay");

  document.getElementById("drawerTitle").textContent = job.title;
  document.getElementById("drawerCompany").textContent = job.company || "Company not listed";

  const salary = formatSalary(job.salary_min, job.salary_max, job.salary_is_predicted);
  document.getElementById("drawerSalary").textContent = salary || "Not specified";
  document.getElementById("drawerLocation").textContent = job.location || "Not specified";
  document.getElementById("drawerType").textContent = formatContractTime(job.contract_time);
  document.getElementById("drawerPosted").textContent = formatDate(job.created) || "Recently";
  document.getElementById("drawerDescription").textContent = stripHtml(job.description || "No description provided.");
  document.getElementById("drawerApplyBtn").href = job.url || "#";

  const logoEl = document.getElementById("drawerLogo");
  logoEl.textContent = (job.company || "?").slice(0, 2).toUpperCase();

  drawer?.classList.add("open");
  overlay?.classList.add("open");
  document.body.style.overflow = "hidden";
}

function closeDrawer() {
  document.getElementById("jobDrawer")?.classList.remove("open");
  document.getElementById("drawerOverlay")?.classList.remove("open");
  document.body.style.overflow = "";
  state.activeJob = null;
}


// ── Save job (stub — full implementation in Saved Jobs feature) ───────────────
async function handleSave(job, btn) {
  if (!Auth.isLoggedIn()) {
    showToast("Create a free account to save jobs to your board.", "info");
    setTimeout(() => {
      window.location.href = "/register.html?next=/search.html";
    }, 900);
    return;
  }
  const original = btn?.innerHTML;
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Saving...";
  }
  try {
    await api.post("/saved-jobs", { external_id: job.external_id });
    showToast("Job saved to your board", "success");
    if (btn) btn.textContent = "Saved";
  } catch (err) {
    showToast(err.detail || "Could not save job", "error");
    if (btn) btn.innerHTML = original;
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function searchJobs() {
  const query = document.getElementById("query")?.value.trim() || "developer";
  const results = document.getElementById("results");
  if (!results) return;

  results.innerHTML = "<p>Searching...</p>";
  try {
    const data = await api.get(`/search/jobs?keywords=${encodeURIComponent(query)}`);
    results.innerHTML = data.jobs.map(job => `
      <div class="card">
        <h3>${escHtml(job.title)}</h3>
        <div class="company">${escHtml(job.company || "Company not listed")} - ${escHtml(job.location || "Remote")}</div>
        <p>${escHtml(stripHtml(job.description || "")).slice(0, 180)}</p>
        <button class="btn" data-external-id="${escHtml(job.external_id)}">Save Job</button>
      </div>
    `).join("");

    results.querySelectorAll("button[data-external-id]").forEach((button, index) => {
      button.addEventListener("click", () => handleSave(data.jobs[index], button));
    });
  } catch (err) {
    results.innerHTML = `<p>${escHtml(err.detail || "Search failed")}</p>`;
  }
}


// ── Helpers ───────────────────────────────────────────────────────────────────
function setupPublicNav() {
  const avatar = document.getElementById("navAvatar");
  const actions = document.querySelector(".app-nav .nav-actions");
  if (!actions) return;

  if (Auth.isLoggedIn()) {
    avatar?.classList.remove("hidden");
    return;
  }

  avatar?.classList.add("hidden");
  if (!document.getElementById("publicNavLinks")) {
    actions.insertAdjacentHTML("beforeend", `
      <div class="public-nav-links" id="publicNavLinks">
        <a href="/login.html">Login</a>
        <a class="nav-cta" href="/register.html">Start free</a>
      </div>
    `);
  }
}

function formatSalary(min, max, predicted) {
  const fmt = (n) => n >= 1000 ? `£${(n / 1000).toFixed(0)}k` : `£${n}`;
  if (!min && !max) return "";
  const range = min && max ? `${fmt(min)} – ${fmt(max)}`
    : min ? `From ${fmt(min)}`
      : `Up to ${fmt(max)}`;
  return range + (predicted ? " (est.)" : "");
}

function formatDate(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  const now = new Date();
  const diff = Math.floor((now - date) / 864e5);
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  if (diff < 7) return `${diff} days ago`;
  if (diff < 30) return `${Math.floor(diff / 7)} weeks ago`;
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

function formatContractTime(ct) {
  return ct === "full_time" ? "Full-time"
    : ct === "part_time" ? "Part-time"
      : "Not specified";
}

function stripHtml(html) {
  return html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

function escHtml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}


// ── Toast notifications ───────────────────────────────────────────────────────
function showToast(msg, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const icons = { success: "✓", error: "✕", info: "ℹ" };
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${icons[type] || "ℹ"}</span>
    <span class="toast-msg">${escHtml(msg)}</span>
    <button class="toast-close" onclick="this.closest('.toast').remove()">×</button>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}
