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
    document.getElementById("jobDetailRoot").innerHTML = `
      <div class="empty-state">
        <h3>Job not found</h3>
        <p>${escHtml(err.detail || "This job is not available.")}</p>
        <a class="btn" href="search.html">Back to search</a>
      </div>`;
  }
}

function renderJobDetail(job) {
  const salary = formatSalary(job.salary_min, job.salary_max);
  const applyUrl = job.application_url || job.url || "";
  const mailTo = job.application_email
    ? `mailto:${job.application_email}?subject=${encodeURIComponent(`Application for ${job.title}`)}`
    : "";
  const roleOverview = buildRoleOverview(job);
  const responsibilities = job.responsibilities || buildFallbackResponsibilities(job);
  const requirements = job.requirements || buildFallbackRequirements(job);
  const additionalQualifications = job.additional_qualifications || buildAdditionalQualifications(job);
  const scheduleExpectations = job.schedule_expectations || buildScheduleExpectations(job);
  const benefits = job.benefits || buildFallbackBenefits(job);
  const companyDescription = job.company_description || buildCompanyDescription(job);
  const jobType = formatJobType(job);
  const experience = formatExperience(job);
  const workStyle = formatWorkStyle(job);
  const hasApplyUrl = applyUrl && applyUrl !== "#";

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
        <div class="job-detail-block job-description-block">
          <span class="eyebrow">Description</span>
          <h2>Job description</h2>
          <p>${escHtml(roleOverview)}</p>
        </div>
        <div class="job-detail-block">
          <span class="eyebrow">Company</span>
          <h2>About the company</h2>
          <p>${escHtml(companyDescription)}</p>
        </div>
        ${section("What you will do", responsibilities)}
        ${section("Required qualifications", requirements)}
        ${section("Additional qualifications that help in interviews", additionalQualifications)}
        ${section("Company demands and schedule", scheduleExpectations)}
        ${section("Benefits", benefits)}
        ${section("Application instructions", job.application_instructions)}
      </article>

      <aside class="job-detail-side glass-card">
        <div class="apply-panel-head">
          <span class="eyebrow">Application</span>
          <h2>Apply</h2>
        </div>
        <div class="detail-facts">
          <span>Location <strong>${escHtml(job.location || "Not specified")}</strong></span>
          <span>Salary <strong>${escHtml(salary || "Not specified")}</strong></span>
          <span>Job type <strong>${escHtml(jobType)}</strong></span>
          <span>Work style <strong>${escHtml(workStyle)}</strong></span>
          <span>Experience <strong>${escHtml(experience)}</strong></span>
          <span>Deadline <strong>${escHtml(job.deadline || "Open")}</strong></span>
        </div>

        <div class="apply-methods">
          <button class="btn" type="button" onclick="openApplicationForm(true)">Apply</button>
          <button class="btn btn-ghost" type="button" onclick="openApplicationForm(false)">Apply with different details</button>
          ${hasApplyUrl ? `<button class="btn" type="button" onclick="openExternalApplication('${encodeURIComponent(applyUrl)}')">Apply on website</button>` : ""}
          ${mailTo ? `<button class="btn btn-ghost" type="button" onclick="openExternalApplication('${encodeURIComponent(mailTo)}')">Apply by email</button>` : ""}
          ${!hasApplyUrl && !mailTo ? `<p class="detail-note">The employer has not added a direct apply link yet. Save this role and follow the application instructions above.</p>` : ""}
        </div>

        <a class="btn btn-ghost" href="search.html">Back to search</a>
      </aside>
    </section>

    <div class="modal-overlay hidden" id="applicationModal" role="dialog" aria-modal="true" aria-labelledby="applicationTitle">
      <form class="application-modal glass-card" id="applicationForm">
        <div class="profile-section-head">
          <div>
            <span class="eyebrow">Apply to ${escHtml(job.company || "company")}</span>
            <h2 id="applicationTitle">Send application</h2>
          </div>
          <button class="icon-btn" type="button" onclick="closeApplicationForm()" aria-label="Close application form">x</button>
        </div>
        <label class="application-check">
          <input type="checkbox" name="use_profile" checked>
          Use my profile details where available
        </label>
        <div class="application-form-grid">
          <label>Full name<input name="applicant_name" required></label>
          <label>Email<input name="applicant_email" type="email" required></label>
          <label>Phone<input name="applicant_phone"></label>
          <label>Headline<input name="headline" placeholder="Frontend Developer, Final Year CS Student"></label>
          <label>Location<input name="location"></label>
          <label>LinkedIn URL<input name="linkedin_url"></label>
          <label>GitHub URL<input name="github_url"></label>
          <label>Portfolio URL<input name="portfolio_url"></label>
          <label class="application-wide">Resume URL<input name="resume_url" placeholder="Paste resume link or profile resume URL"></label>
          <label class="application-wide">Cover letter<textarea name="cover_letter" rows="5" placeholder="Write a short message for the company."></textarea></label>
          <label class="application-wide">Different or extra details<textarea name="extra_details" rows="4" placeholder="Anything different from your profile, notice period, salary expectation, availability, etc."></textarea></label>
        </div>
        <button class="btn" type="submit">Submit application</button>
      </form>
    </div>`;

  const applicationForm = document.getElementById("applicationForm");
  applicationForm?.addEventListener("submit", submitApplication);
  applicationForm?.querySelectorAll("input, textarea").forEach(field => {
    field.addEventListener("input", () => clearApplicationError(field));
  });
}

function section(title, content) {
  if (!content) return "";
  return `<section class="job-detail-section"><h2>${escHtml(title)}</h2><p>${escHtml(content)}</p></section>`;
}

function buildRoleOverview(job) {
  if (job.role_overview) return job.role_overview;
  const base = stripHtml(job.description || "");
  if (base.length > 120) return base;
  return `${job.company || "The company"} is hiring for ${job.title || "this role"}${job.location ? ` in ${job.location}` : ""}. In this position you will support the team inside the company by turning business needs into finished work, coordinating with managers and teammates, communicating progress clearly, and owning practical outcomes from planning through delivery.`;
}

function buildCompanyDescription(job) {
  return `${job.company || "The hiring company"} is looking for someone who can add reliable execution, clear communication, and strong ownership to the team. Review the employer website and application page for the latest company background before applying.`;
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
    "Good understanding of the tools and workflows normally used in this job area.",
    "Strong communication skills and the ability to work independently as well as with a team.",
    `${formatExperience(job)} experience or equivalent practical ability.`,
    "Comfort using the tools, processes, and collaboration style required by the hiring team.",
  ].join(" ");
}

function buildAdditionalQualifications(job) {
  return [
    formatWorkStyle(job) ? `Experience working in a ${formatWorkStyle(job)} environment is helpful.` : "Experience across remote, hybrid, or in-office teams is helpful.",
    "A portfolio, prior project examples, certifications, open-source work, or measurable achievements can strengthen your application.",
    "Interview advantage: show examples of previous work, explain your decision-making, and connect your experience to the company's goals.",
    "Domain experience in similar companies or industries is a plus, but not always required.",
  ].join(" ");
}

function buildScheduleExpectations(job) {
  const location = String(job.location || "").toLowerCase();
  const remoteHint = location.includes("remote")
    ? "The role appears remote-friendly, with regular online communication expected."
    : "The role may include office or hybrid collaboration depending on the employer's policy.";
  return [
    `Expected job type: ${formatJobType(job)}.`,
    `Work style: ${formatWorkStyle(job)}. ${remoteHint}`,
    "Candidates should be reliable with deadlines, follow-through, meetings, and status updates.",
    "Ask the company directly about working days, core hours, weekend support, travel, and remote-day policy during the interview.",
  ].join(" ");
}

function buildFallbackBenefits(job) {
  return [
    "Benefits depend on the employer package and may include paid leave, flexible working, learning support, equipment, health coverage, bonuses, or career progression.",
    job.location && job.location.toLowerCase().includes("remote")
      ? "Remote-friendly work can reduce commute time and support better flexibility."
      : "Ask about flexibility, leave policy, equipment, growth opportunities, and performance bonuses during the interview process.",
  ].join(" ");
}

async function saveDetailJob() {
  if (!Auth.isLoggedIn()) {
    window.location.href = `register.html?next=${encodeURIComponent(window.location.pathname + window.location.search)}`;
    return;
  }
  try {
    await api.post("/saved-jobs", { external_id: detailJob.external_id });
    showToast("Job saved to your board", "success");
  } catch (err) {
    showToast(err.detail || "Could not save job", "error");
  }
}

async function openApplicationForm(useProfile) {
  if (!Auth.isLoggedIn()) {
    window.location.href = `register.html?next=${encodeURIComponent(window.location.pathname + window.location.search)}`;
    return;
  }
  const modal = document.getElementById("applicationModal");
  const form = document.getElementById("applicationForm");
  modal?.classList.remove("hidden");
  form.elements.use_profile.checked = useProfile;
  await prefillApplicationForm(useProfile);
}

function openExternalApplication(encodedUrl) {
  if (!Auth.isLoggedIn()) {
    window.location.href = `register.html?next=${encodeURIComponent(window.location.pathname + window.location.search)}`;
    return;
  }
  const url = decodeURIComponent(encodedUrl || "");
  if (url) window.open(url, "_blank", "noopener,noreferrer");
}

function closeApplicationForm() {
  document.getElementById("applicationModal")?.classList.add("hidden");
}

async function prefillApplicationForm(useProfile) {
  const form = document.getElementById("applicationForm");
  if (!form) return;
  try {
    const user = await api.get("/auth/me");
    form.elements.applicant_name.value = user.full_name || "";
    form.elements.applicant_email.value = user.email || "";
    if (!useProfile) return;
    const profile = await api.get("/profile/me");
    form.elements.applicant_phone.value = profile.phone || "";
    form.elements.headline.value = profile.headline || "";
    form.elements.location.value = profile.location || "";
    form.elements.linkedin_url.value = profile.linkedin_url || "";
    form.elements.github_url.value = profile.github_url || "";
    form.elements.portfolio_url.value = profile.portfolio_url || "";
    form.elements.resume_url.value = profile.resume_url || "";
  } catch (err) {
    showToast(err.detail || "Could not load profile details", "error");
  }
}

async function submitApplication(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (!validateApplicationForm(form)) {
    showToast("Check the highlighted application fields.", "error");
    return;
  }
  const payload = Object.fromEntries(new FormData(form).entries());
  payload.external_id = detailJob.external_id;
  payload.use_profile = form.elements.use_profile.checked;
  try {
    await api.post("/applications", payload);
    showToast("Application sent. The company has been notified.", "success");
    closeApplicationForm();
  } catch (err) {
    showToast(err.detail || "Could not submit application", "error");
  }
}

function validateApplicationForm(form) {
  clearApplicationErrors(form);
  let valid = true;
  if (!requireApplicationField(form.elements.applicant_name, "Enter your full name.")) valid = false;
  if (!requireApplicationField(form.elements.applicant_email, "Enter your email address.")) valid = false;
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.elements.applicant_email.value.trim())) {
    valid = setApplicationError(form.elements.applicant_email, "Enter a valid email address.");
  }
  ["linkedin_url", "github_url", "portfolio_url", "resume_url"].forEach(name => {
    const field = form.elements[name];
    if (field?.value.trim() && !isValidApplicationUrl(field.value.trim())) {
      valid = setApplicationError(field, "Use a full URL that starts with http:// or https://.");
    }
  });
  return valid;
}

function requireApplicationField(field, message) {
  return field?.value?.trim() ? true : setApplicationError(field, message);
}

function clearApplicationErrors(form) {
  form.querySelectorAll(".error, .is-invalid").forEach(field => {
    field.classList.remove("error", "is-invalid");
    field.removeAttribute("aria-invalid");
  });
  form.querySelectorAll(".field-message").forEach(message => message.remove());
}

function clearApplicationError(field) {
  field.classList.remove("error", "is-invalid");
  field.removeAttribute("aria-invalid");
  const message = document.getElementById(`${field.name}-message`);
  message?.remove();
}

function setApplicationError(field, message) {
  field.classList.add("error", "is-invalid");
  field.setAttribute("aria-invalid", "true");
  const messageId = `${field.name}-message`;
  field.setAttribute("aria-describedby", messageId);
  const messageEl = document.createElement("p");
  messageEl.id = messageId;
  messageEl.className = "field-message";
  messageEl.textContent = message;
  field.closest("label")?.insertAdjacentElement("afterend", messageEl);
  return false;
}

function isValidApplicationUrl(value) {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol);
  } catch (_) {
    return false;
  }
}

function formatSalary(min, max) {
  const fmt = (n) => n >= 1000 ? `$${(n / 1000).toFixed(0)}k` : `$${n}`;
  if (!min && !max) return "";
  return min && max ? `${fmt(min)} - ${fmt(max)}` : min ? `From ${fmt(min)}` : `Up to ${fmt(max)}`;
}

function formatJobType(job) {
  const value = job.employment_type || job.contract_time || job.contract_type || "";
  const normalized = String(value).replace(/_/g, " ").trim();
  if (!normalized) return "Full-time or company-defined";
  return normalized.replace(/\b\w/g, char => char.toUpperCase());
}

function formatExperience(job) {
  if (job.experience_level) return job.experience_level;
  const title = String(job.title || "").toLowerCase();
  if (["senior", "lead", "principal", "staff"].some(word => title.includes(word))) return "Senior level";
  if (["junior", "graduate", "intern", "entry"].some(word => title.includes(word))) return "Entry level";
  if (["manager", "head", "director"].some(word => title.includes(word))) return "Leadership level";
  return "Mid level";
}

function formatWorkStyle(job) {
  if (job.work_style) return job.work_style;
  const location = String(job.location || "").toLowerCase();
  if (location.includes("remote")) return "Remote";
  if (location.includes("hybrid")) return "Hybrid";
  return "On-site or hybrid";
}

function stripHtml(html) {
  return String(html || "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

function showToast(msg, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span class="toast-icon">${type === "success" ? "OK" : "!"}</span><span>${escHtml(msg)}</span><a href="jobs.html">View board</a>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

function escHtml(str) {
  return String(str || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function escAttr(str) {
  return escHtml(str).replace(/'/g, "&#39;");
}
