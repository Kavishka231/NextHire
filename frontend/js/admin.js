let adminUsersPage = 1;
let adminJobsPage = 1;
let adminNotesPage = 1;
const adminPageSize = 25;

async function initAdmin() {
  if (!(await requireAuth())) return;
  bindAdminEvents();
  await loadAdmin();
}

function bindAdminEvents() {
  document.getElementById("adminUserSearch")?.addEventListener("input", debounce(() => loadUsers(1), 250));
  document.getElementById("featuredJobForm")?.addEventListener("submit", addFeaturedJob);
  document.getElementById("broadcastForm")?.addEventListener("submit", sendBroadcast);
  document.getElementById("adminCreateForm")?.addEventListener("submit", createAdmin);
}

async function loadAdmin() {
  try {
    await Promise.all([loadSummary(), loadUsers(), loadCompanies(), loadJobs(), loadModeration(), loadAnalytics(), loadEmailPreview(), loadHealth()]);
  } catch (err) {
    if (err.status === 403) {
      showToast("Admin access required. Login with the dev admin account.", "error");
      setTimeout(() => { window.location.href = "login.html"; }, 1200);
      return;
    }
    showToast(err.detail || "Could not load admin dashboard", "error");
  }
}

async function loadCompanies() {
  const companies = await api.get("/admin/companies/pending");
  document.getElementById("pendingCompanies").innerHTML = companies.length ? companies.map(company => `
    <div class="admin-list-item">
      <strong>${escHtml(company.company_name || company.full_name)}</strong>
      <span>${escHtml(company.email)} · ${escHtml(company.company_status)}</span>
      <p>${escHtml(company.company_website || "No website provided")}</p>
      <div>
        <button onclick="approveCompany(${company.id}, true)">Approve</button>
        <button onclick="approveCompany(${company.id}, false)">Reject</button>
      </div>
    </div>
  `).join("") : `<div class="chart-empty">No pending company accounts.</div>`;
}

async function loadSummary() {
  const data = await api.get("/admin/summary");
  const items = [
    ["Users", data.total_users],
    ["New this week", data.new_users_week],
    ["Jobs cached", data.total_jobs],
    ["Searches", data.total_searches],
    ["Saved jobs", data.total_saved],
    ["Applications", data.total_applications],
  ];
  document.getElementById("adminSummary").innerHTML = items.map(([label, value]) => `
    <div class="kpi-card glass-card"><span>${escHtml(label)}</span><strong>${value ?? 0}</strong></div>
  `).join("");
}

async function loadUsers(page = adminUsersPage) {
  const q = document.getElementById("adminUserSearch")?.value || "";
  const data = await api.get(`/admin/users?q=${encodeURIComponent(q)}&${paginationQuery(page, adminPageSize)}`);
  const previousPage = previousPageForEmptyResult(data);
  if (previousPage) return loadUsers(previousPage);
  adminUsersPage = data.page;
  const users = data.items;
  document.getElementById("adminUsers").innerHTML = `
    <thead><tr><th>User</th><th>Joined</th><th>Jobs</th><th>Status</th><th>Actions</th></tr></thead>
    <tbody>${users.map(user => `
      <tr>
        <td><strong>${escHtml(user.full_name)}</strong><small>${escHtml(user.email)} · ${escHtml(user.admin_role)}</small></td>
        <td>${dateOnly(user.join_date)}</td>
        <td>${user.saved_jobs} saved / ${user.applied_jobs} applied</td>
        <td>${user.is_active ? "Active" : "Inactive"} · ${user.is_verified ? "Verified" : "Unverified"}</td>
        <td>
          <button onclick="toggleUser(${user.id}, ${!user.is_active}, 'is_active')">${user.is_active ? "Deactivate" : "Activate"}</button>
          <button onclick="toggleUser(${user.id}, true, 'is_verified')">Verify</button>
          <button onclick="resetUserPassword(${user.id})">Reset pass</button>
          <button onclick="deleteUser(${user.id})">Delete</button>
        </td>
      </tr>
    `).join("")}</tbody>`;
  renderCollectionPagination("adminUsers", data, loadUsers);
}

async function loadJobs(page = adminJobsPage) {
  const data = await api.get(`/admin/jobs?${paginationQuery(page, adminPageSize)}`);
  const previousPage = previousPageForEmptyResult(data);
  if (previousPage) return loadJobs(previousPage);
  adminJobsPage = data.page;
  const jobs = data.items;
  document.getElementById("adminJobs").innerHTML = `
    <thead><tr><th>Job</th><th>Location</th><th>Popularity</th><th>Actions</th></tr></thead>
    <tbody>${jobs.map(job => `
      <tr>
        <td><strong>${escHtml(job.title)}</strong><small>${escHtml(job.company || "")} ${job.is_featured ? "· Featured" : ""}</small></td>
        <td>${escHtml(job.location || "")}</td>
        <td>${job.saved_count} saved / ${job.application_count} applications</td>
        <td>
          <button onclick="renameJob(${job.id}, '${escAttr(job.title)}')">Update</button>
          <button onclick="toggleFeatured(${job.id}, ${!job.is_featured})">${job.is_featured ? "Unfeature" : "Feature"}</button>
          <button onclick="deleteJob(${job.id})">Delete</button>
        </td>
      </tr>
    `).join("")}</tbody>`;
  renderCollectionPagination("adminJobs", data, loadJobs);
}

async function loadModeration(page = adminNotesPage) {
  const [notes, profiles] = await Promise.all([
    api.get(`/admin/moderation/notes?${paginationQuery(page, adminPageSize)}`),
    api.get("/admin/moderation/profiles"),
  ]);
  const previousPage = previousPageForEmptyResult(notes);
  if (previousPage) return loadModeration(previousPage);
  adminNotesPage = notes.page;
  document.getElementById("adminNotes").innerHTML = notes.items.length ? notes.items.map(note => `
    <div class="admin-list-item"><span>${escHtml(note.user_email)}</span><p>${escHtml(note.content)}</p><button onclick="deleteNote(${note.id})">Delete</button></div>
  `).join("") : `<div class="chart-empty">No notes yet.</div>`;
  renderCollectionPagination("adminNotes", notes, loadModeration);
  document.getElementById("adminProfiles").innerHTML = profiles.length ? profiles.map(row => `
    <div class="admin-list-item"><span>${escHtml(row.user.email)}</span><p>${escHtml(row.profile?.headline || row.profile?.bio || "No public text")}</p><button onclick="clearProfile(${row.profile.id})">Clear content</button></div>
  `).join("") : `<div class="chart-empty">No profiles yet.</div>`;
}

async function loadAnalytics() {
  const data = await api.get("/admin/analytics");
  document.getElementById("adminAnalytics").innerHTML = `
    ${listBlock("Conversion funnel", Object.entries(data.conversion_funnel).map(([label, count]) => ({ label, count })))}
    ${listBlock("Top keywords", data.top_keywords)}
    ${listBlock("Popular locations", data.top_locations)}
    ${listBlock("Popular categories", data.top_categories)}
  `;
}

async function loadEmailPreview() {
  const data = await api.get("/admin/email/reminder-preview");
  document.getElementById("emailPreview").textContent = `${data.subject}\n\n${data.html}`;
}

async function loadHealth() {
  const data = await api.get("/admin/health");
  document.getElementById("adminHealth").innerHTML = Object.entries(data).map(([key, value]) => `
    <div class="admin-list-item"><span>${escHtml(key.replaceAll("_", " "))}</span><strong>${escHtml(String(value))}</strong></div>
  `).join("");
}

async function toggleUser(id, value, field) {
  await api.patch(`/admin/users/${id}`, { [field]: value });
  showToast("User updated", "success");
  loadUsers();
}

async function approveCompany(id, approved) {
  await api.patch(`/admin/companies/${id}/approval`, { approved });
  showToast(approved ? "Company approved" : "Company rejected", "success");
  loadCompanies();
  loadUsers();
}

async function resetUserPassword(id) {
  const newPassword = prompt("New password for this user:");
  if (!newPassword) return;
  await api.post(`/admin/users/${id}/reset-password`, { new_password: newPassword });
  showToast("Password reset", "success");
}

async function deleteUser(id) {
  if (!confirm("Delete this user permanently?")) return;
  await api.delete(`/admin/users/${id}`);
  showToast("User deleted", "success");
  loadUsers();
}

async function deleteJob(id) {
  if (!confirm("Delete this job listing?")) return;
  await api.delete(`/admin/jobs/${id}`);
  showToast("Job deleted", "success");
  loadJobs();
}

async function renameJob(id, currentTitle) {
  const title = prompt("Update job title:", currentTitle);
  if (!title) return;
  await api.patch(`/admin/jobs/${id}`, { title });
  showToast("Job updated", "success");
  loadJobs();
}

async function toggleFeatured(id, isFeatured) {
  await api.patch(`/admin/jobs/${id}`, { is_featured: isFeatured });
  showToast("Job updated", "success");
  loadJobs();
}

async function deleteNote(id) {
  await api.delete(`/admin/moderation/notes/${id}`);
  showToast("Note deleted", "success");
  loadModeration();
}

async function clearProfile(id) {
  await api.patch(`/admin/moderation/profiles/${id}`, { clear_avatar_url: true, clear_headline: true, clear_bio: true });
  showToast("Profile content cleared", "success");
  loadModeration();
}

async function addFeaturedJob(event) {
  event.preventDefault();
  const form = event.currentTarget;
  await api.post("/admin/jobs", Object.fromEntries(new FormData(form).entries()));
  form.reset();
  showToast("Featured job added", "success");
  adminJobsPage = 1;
  loadJobs(1);
}

async function sendBroadcast(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const data = await api.post("/admin/email/broadcast", Object.fromEntries(new FormData(form).entries()));
  showToast(data.message, "success");
}

async function createAdmin(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const values = Object.fromEntries(new FormData(form).entries());
  const role = values.role;
  delete values.role;
  await api.post(`/admin/admins?role=${encodeURIComponent(role)}`, values);
  form.reset();
  showToast("Admin account created", "success");
  loadUsers();
}

function listBlock(title, rows) {
  return `<div class="admin-list-item"><strong>${escHtml(title)}</strong>${
    rows.length ? rows.map(row => `<span>${escHtml(row.label)}: ${row.count}</span>`).join("") : `<span>No data yet</span>`
  }</div>`;
}

function debounce(fn, wait) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

function dateOnly(value) {
  return value ? new Date(value).toLocaleDateString() : "Never";
}

function showToast(msg, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span class="toast-msg">${escHtml(msg)}</span><button class="toast-close" type="button">x</button>`;
  toast.querySelector("button").addEventListener("click", () => toast.remove());
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

function escHtml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escAttr(str) {
  return escHtml(str).replace(/'/g, "&#39;");
}
