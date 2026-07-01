let savedJobs = [];
let boardView = "kanban";

const statusConfig = [
  ["saved", "Saved"],
  ["applied", "Applied"],
  ["interview", "Interview"],
  ["offer", "Offer"],
  ["rejected", "Rejected"],
];

async function initJobs() {
  if (!requireAuth()) return;
  bindBoardControls();
  await loadJobsUser();
  await loadJobs();
}

function bindBoardControls() {
  document.getElementById("viewKanban")?.addEventListener("click", () => switchView("kanban"));
  document.getElementById("viewList")?.addEventListener("click", () => switchView("list"));
  document.getElementById("notesCloseBtn")?.addEventListener("click", closeNotes);
  document.getElementById("notesOverlay")?.addEventListener("click", closeNotes);
}

async function loadJobsUser() {
  try {
    const user = await api.get("/auth/me");
    const fullName = user.full_name || "User";
    const initials = fullName.split(" ").map(part => part[0]).join("").toUpperCase().slice(0, 2);
    setText("navInitials", initials);
    setText("navUserName", fullName);
    setText("navUserEmail", user.email);
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
  setText("totalJobsCount", jobs.length);
  updateTabCounts(jobs);
  if (boardView === "list") renderList(jobs);
  else renderKanban(jobs);
}

function renderKanban(jobs) {
  const board = document.getElementById("kanbanBoard");
  const list = document.getElementById("listViewContainer");
  if (list) list.style.display = "none";
  if (!board) return;
  board.style.display = "";
  board.innerHTML = statusConfig.map(([status, label]) => {
    const items = jobs.filter(item => item.status === status);
    return `
      <section class="kanban-column glass-card">
        <div class="kanban-column-header"><span>${label}</span><strong>${items.length}</strong></div>
        <div class="kanban-column-body">
          ${items.length ? items.map(savedJobCard).join("") : `<div class="empty-mini">No ${label.toLowerCase()} jobs</div>`}
        </div>
      </section>`;
  }).join("");
}

function renderList(jobs) {
  const board = document.getElementById("kanbanBoard");
  const list = document.getElementById("listViewContainer");
  if (board) board.style.display = "none";
  if (!list) return;
  list.style.display = "";
  list.innerHTML = jobs.length ? jobs.map(listRow).join("") : `<div class="chart-empty">No saved jobs yet.</div>`;
  list.querySelectorAll("[data-status-select]").forEach(select => {
    select.addEventListener("change", () => updateStatus(select.dataset.id, select.value));
  });
}

function savedJobCard(savedJob) {
  const job = savedJob.job || {};
  return `
    <article class="job-card glass-card">
      <div class="job-card-top">
        <span>${escHtml(job.company || "Company")}</span>
        <button type="button" onclick="openNotes('${savedJob.id}', '${escAttr(job.title || "Saved job")}')">Notes</button>
      </div>
      <h3>${escHtml(job.title || "Saved job")}</h3>
      <p>${escHtml(job.location || "Remote / flexible")}</p>
      <select onchange="updateStatus('${savedJob.id}', this.value)">
        ${statusConfig.map(([status, label]) => `<option value="${status}" ${savedJob.status === status ? "selected" : ""}>${label}</option>`).join("")}
      </select>
    </article>`;
}

function listRow(savedJob) {
  const job = savedJob.job || {};
  return `
    <div class="list-row glass-card">
      <div><strong>${escHtml(job.title || "Saved job")}</strong><span>${escHtml(job.company || "Company")} · ${escHtml(job.location || "Remote")}</span></div>
      <select data-status-select data-id="${savedJob.id}">
        ${statusConfig.map(([status, label]) => `<option value="${status}" ${savedJob.status === status ? "selected" : ""}>${label}</option>`).join("")}
      </select>
      <button class="btn btn-ghost" type="button" onclick="openNotes('${savedJob.id}', '${escAttr(job.title || "Saved job")}')">Notes</button>
    </div>`;
}

function switchView(view) {
  boardView = view;
  document.getElementById("viewKanban")?.classList.toggle("active", view === "kanban");
  document.getElementById("viewList")?.classList.toggle("active", view === "list");
  document.getElementById("statusTabsBar").style.display = view === "list" ? "" : "none";
  renderSavedJobs(savedJobs);
}

async function updateStatus(savedJobId, status) {
  try {
    await api.patch(`/saved-jobs/${savedJobId}/status`, { status });
    await loadJobs();
  } catch (err) {
    alert(err.detail || err.message);
  }
}

function updateTabCounts(jobs) {
  document.querySelectorAll(".status-tab").forEach(tab => {
    const status = tab.dataset.status;
    const count = status === "all" ? jobs.length : jobs.filter(job => job.status === status).length;
    const el = tab.querySelector(".status-tab-count");
    if (el) el.textContent = count;
  });
}

function openNotes(savedJobId, title) {
  setText("notesPanelTitle", title);
  setText("notesPanelSubtitle", `Saved job #${savedJobId}`);
  const panel = document.getElementById("notesPanel");
  const overlay = document.getElementById("notesOverlay");
  panel?.classList.add("open");
  overlay?.classList.add("open");
}

function closeNotes() {
  document.getElementById("notesPanel")?.classList.remove("open");
  document.getElementById("notesOverlay")?.classList.remove("open");
}

async function saveJob(jobId) {
  try {
    await api.post("/saved-jobs", { job_id: jobId });
    await loadJobs();
  } catch (err) {
    alert(err.detail || err.message);
  }
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
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
