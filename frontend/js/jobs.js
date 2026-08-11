let savedJobs = [];
let savedJobsPage = 1;
const savedJobsPageSize = 25;

const statusConfig = [
  ["saved", "Saved"],
  ["applied", "Applied"],
  ["interview", "Interview"],
  ["offer", "Offer"],
  ["rejected", "Rejected"],
];

async function initJobs() {
  if (!(await requireAuth())) return;
  bindBoardControls();
  await loadJobsUser();
  await loadJobs();
}

function bindBoardControls() {
  document.getElementById("notesCloseBtn")?.addEventListener("click", closeNotes);
  document.getElementById("notesOverlay")?.addEventListener("click", closeNotes);
  document.getElementById("noteSubmitBtn")?.addEventListener("click", addNote);
}

async function loadJobsUser() {
  await loadCurrentUserNav();
}

async function loadJobs(page = savedJobsPage) {
  try {
    const data = await api.get(`/saved-jobs?${paginationQuery(page, savedJobsPageSize)}`);
    const previousPage = previousPageForEmptyResult(data);
    if (previousPage) return loadJobs(previousPage);
    savedJobsPage = data.page;
    savedJobs = data.items;
    renderSavedJobs(savedJobs, data);
  } catch (err) {
    if (err.status === 401) logout();
    console.error(err);
  }
}

function renderSavedJobs(jobs, pageData) {
  setText("totalJobsCount", pageData.total);
  updateTabCounts(jobs, pageData.total);
  renderList(jobs);
  renderCollectionPagination("listViewContainer", pageData, loadJobs);
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

function updateTabCounts(jobs, total) {
  document.querySelectorAll(".status-tab").forEach(tab => {
    const status = tab.dataset.status;
    const count = status === "all" ? total : jobs.filter(job => job.status === status).length;
    const el = tab.querySelector(".status-tab-count");
    if (el) el.textContent = count;
  });
}

async function openNotes(savedJobId, title) {
  document.getElementById("notesPanel").dataset.savedJobId = savedJobId;
  setText("notesPanelTitle", title);
  setText("notesPanelSubtitle", `Saved job #${savedJobId}`);
  const panel = document.getElementById("notesPanel");
  const overlay = document.getElementById("notesOverlay");
  panel?.classList.add("open");
  overlay?.classList.add("open");
  await loadNotes(savedJobId);
}

async function loadNotes(savedJobId) {
  const root = document.getElementById("notesList");
  if (!root) return;
  try {
    const data = await api.get(`/notes/job/${savedJobId}?page=1&page_size=25`);
    root.innerHTML = data.items.length
      ? data.items.map(note => `<div class="note-item"><p>${escHtml(note.content)}</p></div>`).join("")
      : `<div class="chart-empty">No notes yet.</div>`;
  } catch (err) {
    root.innerHTML = `<div class="chart-empty">${escHtml(err.detail || "Could not load notes")}</div>`;
  }
}

async function addNote() {
  const panel = document.getElementById("notesPanel");
  const input = document.getElementById("noteInput");
  const savedJobId = panel?.dataset.savedJobId;
  const content = input?.value.trim();
  if (!savedJobId || !content) return;
  await api.post("/notes", { saved_job_id: Number(savedJobId), content });
  input.value = "";
  await loadNotes(savedJobId);
}

function closeNotes() {
  document.getElementById("notesPanel")?.classList.remove("open");
  document.getElementById("notesOverlay")?.classList.remove("open");
}

function escAttr(str) {
  return escHtml(str).replace(/'/g, "&#39;");
}
