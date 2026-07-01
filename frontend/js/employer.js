let employerJobs = [];

async function initEmployer() {
  if (!requireAuth()) return;
  document.getElementById("companyJobForm")?.addEventListener("submit", saveCompanyJob);
  document.getElementById("companyProfileForm")?.addEventListener("submit", saveCompanyProfile);
  document.getElementById("clearJobForm")?.addEventListener("click", clearJobForm);
  await loadEmployer();
}

async function loadEmployer() {
  const user = await api.get("/auth/me");
  const status = document.getElementById("companyStatusText");
  const form = document.getElementById("companyJobForm");
  const profileForm = document.getElementById("companyProfileForm");
  if (user.account_type !== "company") {
    status.innerHTML = `This account is a candidate account. Register as a company to request approval.`;
    form.classList.add("disabled-panel");
    profileForm.classList.add("disabled-panel");
    return;
  }
  profileForm.classList.remove("disabled-panel");
  profileForm.elements.company_name.value = user.company_name || "";
  profileForm.elements.company_website.value = user.company_website || "";
  profileForm.elements.company_description.value = user.company_description || "";
  document.getElementById("companyVerifiedBadge").classList.toggle("hidden", !user.company_verified);
  if (user.company_status !== "approved" || !user.company_verified) {
    status.innerHTML = `Company status: <strong>${escHtml(user.company_status)}</strong>. Your job posting tools are waiting for admin approval.`;
    form.classList.add("disabled-panel");
    document.getElementById("companyJobsList").innerHTML = `<div class="empty-mini">Pending approval. You can fill company details now; job posting unlocks after admin verification.</div>`;
    return;
  }
  status.innerHTML = `${escHtml(user.company_name || user.full_name)} <span class="verified-badge">Verified company</span>`;
  form.classList.remove("disabled-panel");
  employerJobs = await api.get("/jobs/company/mine");
  renderEmployerJobs();
}

async function saveCompanyProfile(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (form.classList.contains("disabled-panel")) return;
  const payload = Object.fromEntries(new FormData(form).entries());
  const data = await api.put("/company/me", payload);
  showToast(data.company_status === "pending" ? "Company details saved and sent for review" : "Company details saved", "success");
  await loadEmployer();
}

function renderEmployerJobs() {
  const root = document.getElementById("companyJobsList");
  root.innerHTML = employerJobs.length ? employerJobs.map(job => `
    <article class="job-card glass-card">
      <div class="job-card-header">
        <div><strong>${escHtml(job.title)}</strong><p>${escHtml(job.location || "No location")} · ${escHtml(job.employment_type || "Job")}</p></div>
        <span class="verified-badge">Verified</span>
      </div>
      <p>${escHtml(job.description || "").slice(0, 180)}</p>
      <div class="job-card-footer">
        <button class="btn btn-ghost" type="button" onclick="editCompanyJob(${job.id})">Edit</button>
        <button class="btn btn-ghost" type="button" onclick="deleteCompanyJob(${job.id})">Delete</button>
        <a class="btn" href="/job-detail.html?external_id=${encodeURIComponent(job.external_id)}">View</a>
      </div>
    </article>
  `).join("") : `<div class="empty-mini">No company job posts yet.</div>`;
}

async function saveCompanyJob(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (form.classList.contains("disabled-panel")) {
    showToast("Company approval required before posting jobs.", "error");
    return;
  }
  const payload = Object.fromEntries(new FormData(form).entries());
  const jobId = payload.job_id;
  delete payload.job_id;
  ["salary_min", "salary_max"].forEach(key => {
    payload[key] = payload[key] ? Number(payload[key]) : null;
  });
  const job = jobId ? await api.put(`/jobs/company/${jobId}`, payload) : await api.post("/jobs/company", payload);
  showToast(jobId ? "Job updated" : "Job published", "success");
  clearJobForm();
  await loadEmployer();
}

function editCompanyJob(id) {
  const job = employerJobs.find(item => item.id === id);
  if (!job) return;
  const form = document.getElementById("companyJobForm");
  Object.keys(job).forEach(key => {
    if (form.elements[key]) form.elements[key].value = job[key] || "";
  });
  form.elements.job_id.value = job.id;
  form.querySelector("button[type=submit]").textContent = "Update job";
  window.scrollTo({ top: form.offsetTop - 90, behavior: "smooth" });
}

async function deleteCompanyJob(id) {
  if (!confirm("Delete this job post?")) return;
  await api.delete(`/jobs/company/${id}`);
  showToast("Job deleted", "success");
  await loadEmployer();
}

function clearJobForm() {
  const form = document.getElementById("companyJobForm");
  form.reset();
  form.elements.job_id.value = "";
  form.querySelector("button[type=submit]").textContent = "Publish job";
}

function showToast(msg, type = "info") {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

function escHtml(str) {
  return String(str || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
