let savedJobs = [];

async function initJobs() {
  if (!requireAuth()) return;
  await loadJobsUser();
  await loadJobs();
}

async function loadJobsUser() {
  try {
    const user = await api.get("/auth/me");
    const fullName = user.full_name || "User";
    const initials = fullName.split(" ").map(part => part[0]).join("").toUpperCase().slice(0, 2);

    const navInitials = document.getElementById("navInitials");
    if (navInitials) navInitials.textContent = initials;

    const navUserName = document.getElementById("navUserName");
    if (navUserName) navUserName.textContent = fullName;

    const navUserEmail = document.getElementById("navUserEmail");
    if (navUserEmail) navUserEmail.textContent = user.email;
  } catch (err) {
    if (err.status === 401) logout();
  }
}

async function loadJobs() {
  try {
    savedJobs = await api.get("/saved-jobs");
    renderSavedJobs(savedJobs);
  } catch (err) {
    if (err.status === 401) logout();
    console.error(err);
  }
}

function renderSavedJobs(jobs) {
  const count = document.getElementById("totalJobsCount");
  if (count) count.textContent = jobs.length;

  const board = document.getElementById("kanbanBoard");
  if (!board) return;

  const statuses = [
    ["saved", "Saved"],
    ["applied", "Applied"],
    ["interview", "Interview"],
    ["offer", "Offer"],
    ["rejected", "Rejected"],
  ];

  board.innerHTML = statuses.map(([status, label]) => {
    const items = jobs.filter(item => item.status === status);
    return `
      <section class="kanban-column">
        <div class="kanban-column-header">
          <span>${label}</span>
          <span>${items.length}</span>
        </div>
        <div class="kanban-column-body">
          ${items.length ? items.map(savedJobCard).join("") : `<div class="chart-empty">No jobs</div>`}
        </div>
      </section>`;
  }).join("");
}

function savedJobCard(savedJob) {
  const job = savedJob.job || {};
  return `
    <article class="job-card">
      <div class="job-title">${escHtml(job.title || "Saved job")}</div>
      <div class="job-company">${escHtml(job.company || "")}</div>
      <div class="job-meta">${escHtml(job.location || "")}</div>
    </article>`;
}

async function saveJob(jobId) {
  try {
    await api.post("/saved-jobs", { job_id: jobId });
    await loadJobs();
  } catch (err) {
    alert(err.detail || err.message);
  }
}

function escHtml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
