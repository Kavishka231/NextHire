let detailJob = null;

async function initJobDetail() {
  const params = new URLSearchParams(window.location.search);
  const externalId = params.get("external_id");
  const id = params.get("id");
  try {
    detailJob = externalId
      ? await api.get(`/jobs/external/${encodeURIComponent(externalId)}`)
      : await api.get(`/jobs/${encodeURIComponent(id)}`);
    renderJobDetail(detailJob);
  } catch (err) {
    document.getElementById("jobDetailRoot").innerHTML = `<div class="empty-state"><h3>Job not found</h3><p>${escHtml(err.detail || "This job is not available.")}</p><a class="btn" href="/search.html">Back to search</a></div>`;
  }
}

function renderJobDetail(job) {
  const salary = formatSalary(job.salary_min, job.salary_max);
  const applyUrl = job.application_url || job.url || "";
  const mailTo = job.application_email ? `mailto:${job.application_email}?subject=${encodeURIComponent(`Application for ${job.title}`)}` : "";
  const roleOverview = buildRoleOverview(job);
  const responsibilities = job.responsibilities || buildFallbackResponsibilities(job);
  const requirements = job.requirements || buildFallbackRequirements(job);
  const expectations = buildExpectations(job);
  const additionalQualifications = buildAdditionalQualifications(job);
  document.getElementById("jobDetailRoot").innerHTML = `
    <section class="job-detail-hero glass-card">
      <div class="job-company-logo">${escHtml((job.company || "NH").slice(0, 2).toUpperCase())}</div>
      <div>
        <span class="eyebrow">${job.source === "company" ? "Direct company post" : "External job listing"}</span>
        <h1>${escHtml(job.title)}</h1>
        <p>${escHtml(job.company || "Company not listed")} ${job.company_verified ? `<span class="verified-badge">Verified company</span>` : ""}</p>
      </div>
      <button class="btn btn-ghost" type="button" onclick="saveDetailJob()">Save job</button>
    </section>
    <section class="job-detail-layout">
      <article class="job-detail-main glass-card">
        <h2>Role overview</h2>
        <p>${escHtml(roleOverview)}</p>
        ${block("What you will do", responsibilities)}
        ${block("Qualifications", requirements)}
        ${block("What the company expects", expectations)}
        ${block("Additional qualifications", additionalQualifications)}
        ${block("Benefits", job.benefits)}
        ${block("Application instructions", job.application_instructions)}
      </article>
      <aside class="job-detail-side glass-card">
        <h2>Apply</h2>
        <div class="detail-facts">
          <span>Location <strong>${escHtml(job.location || "Not specified")}</strong></span>
          <span>Salary <strong>${escHtml(salary || "Not specified")}</strong></span>
          <span>Job type <strong>${escHtml(job.employment_type || job.work_style || "Not specified")}</strong></span>
          <span>Experience <strong>${escHtml(job.experience_level || "Not specified")}</strong></span>
          <span>Deadline <strong>${escHtml(job.deadline || "Open")}</strong></span>
        </div>
        ${applyUrl ? `<a class="btn" href="${escAttr(applyUrl)}" target="_blank" rel="noreferrer">Apply on website</a>` : ""}
        ${mailTo ? `<a class="btn btn-ghost" href="${escAttr(mailTo)}">Apply by email</a>` : ""}
        <a class="btn btn-ghost" href="/search.html">Back to search</a>
      </aside>
    </section>
  `;
}

function block(title, content) {
  return content ? `<h2>${escHtml(title)}</h2><p>${escHtml(content)}</p>` : "";
}

function buildRoleOverview(job) {
  const base = stripHtml(job.description || "");
  if (base.length > 80) return base;
  return `${job.company || "The company"} is hiring for ${job.title || "this role"}${job.location ? ` in ${job.location}` : ""}. This role is suited for candidates who can contribute clearly, communicate well, and take ownership of practical work from planning through delivery.`;
}

function buildFallbackResponsibilities(job) {
  return [
    `Own day-to-day execution for the ${job.title || "role"} and keep work moving with clear communication.`,
    "Collaborate with team members, managers, and stakeholders to understand requirements and deliver useful outcomes.",
    "Document progress, raise blockers early, and improve workflows where possible.",
    "Contribute to quality, reliability, and a professional user or customer experience.",
  ].join(" ");
}

function buildFallbackRequirements(job) {
  return [
    "Relevant education, training, portfolio work, or practical experience for this role.",
    "Strong communication skills and the ability to work independently as well as with a team.",
    job.experience_level ? `${job.experience_level} level experience or equivalent practical ability.` : "Ability to learn quickly and handle responsibilities with care.",
    "Comfort using the tools, processes, and collaboration style required by the hiring team.",
  ].join(" ");
}

function buildExpectations(job) {
  return [
    "Be reliable with deadlines and follow-through.",
    "Ask thoughtful questions when requirements are unclear.",
    "Bring a problem-solving mindset and communicate tradeoffs honestly.",
    "Respect company processes while looking for ways to improve outcomes.",
  ].join(" ");
}

function buildAdditionalQualifications(job) {
  return [
    job.work_style ? `Experience working in a ${job.work_style} environment is helpful.` : "Experience working across remote, hybrid, or in-office teams is helpful.",
    "A portfolio, prior project examples, certifications, or measurable achievements can strengthen your application.",
    "Domain experience in similar companies or industries is a plus, but not always required.",
  ].join(" ");
}

async function saveDetailJob() {
  if (!Auth.isLoggedIn()) {
    window.location.href = `/register.html?next=${encodeURIComponent(window.location.pathname + window.location.search)}`;
    return;
  }
  try {
    await api.post("/saved-jobs", { external_id: detailJob.external_id });
    showToast("Job saved to your board", "success");
  } catch (err) {
    showToast(err.detail || "Could not save job", "error");
  }
}

function formatSalary(min, max) {
  const fmt = (n) => n >= 1000 ? `$${(n / 1000).toFixed(0)}k` : `$${n}`;
  if (!min && !max) return "";
  return min && max ? `${fmt(min)} - ${fmt(max)}` : min ? `From ${fmt(min)}` : `Up to ${fmt(max)}`;
}

function stripHtml(html) {
  return String(html || "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

function showToast(msg, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span class="toast-icon">${type === "success" ? "✓" : "!"}</span><span>${escHtml(msg)}</span><a href="/jobs.html">View board</a>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

function escHtml(str) {
  return String(str || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function escAttr(str) {
  return escHtml(str).replace(/'/g, "&#39;");
}
