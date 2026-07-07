let savedJobs = [];

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
  document.getElementById("notesCloseBtn")?.addEventListener("click", closeNotes);
  document.getElementById("notesOverlay")?.addEventListener("click", closeNotes);
}

async function loadJobsUser() {
  await loadCurrentUserNav();
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
  renderList(jobs);
}

function renderList(jobs) {
  const list = document.getElementById("listViewContainer");
  if (!list) return;
  list.style.display = "";
  list.innerHTML = jobs.length ? jobs.map(listRow).join("") : `<div class="chart-empty">No saved jobs yet.</div>`;
  list.querySelectorAll("[data-status-select]").forEach(select => {
    select.addEventListener("change", () => updateStatus(select.dataset.id, select.value));
  });
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

function escAttr(str) {
  return escHtml(str).replace(/'/g, "&#39;");
}
