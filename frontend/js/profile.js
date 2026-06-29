const sectionConfigs = [
  {
    key: "work_experience",
    title: "Work experience",
    eyebrow: "Experience",
    addLabel: "Add experience",
    fields: [
      ["title", "Job title"],
      ["company", "Company name"],
      ["start_date", "Start date"],
      ["end_date", "End date or current"],
      ["description", "Description", "textarea"],
    ],
  },
  {
    key: "education",
    title: "Education",
    eyebrow: "Education",
    addLabel: "Add education",
    fields: [
      ["school", "School / university"],
      ["degree", "Degree and field"],
      ["start_year", "Start year"],
      ["end_year", "End year"],
      ["grade", "Grade / GPA"],
    ],
  },
  {
    key: "skills",
    title: "Skills",
    eyebrow: "Skill tags",
    addLabel: "Add skill",
    fields: [
      ["name", "Skill name"],
      ["level", "Level: beginner, intermediate, expert"],
      ["endorsements", "Endorsements"],
    ],
  },
  {
    key: "certifications",
    title: "Certifications and licenses",
    eyebrow: "Credentials",
    addLabel: "Add certification",
    fields: [
      ["name", "Certificate name"],
      ["issuer", "Issuing organisation"],
      ["date", "Date earned"],
      ["url", "Verification URL"],
    ],
  },
  {
    key: "projects",
    title: "Projects",
    eyebrow: "Proof of work",
    addLabel: "Add project",
    fields: [
      ["name", "Project name"],
      ["description", "Description", "textarea"],
      ["stack", "Tech stack used"],
      ["url", "GitHub or live link"],
    ],
  },
  {
    key: "languages",
    title: "Languages",
    eyebrow: "Communication",
    addLabel: "Add language",
    fields: [
      ["name", "Language name"],
      ["proficiency", "Basic, conversational, fluent, native"],
    ],
  },
  {
    key: "volunteer_experience",
    title: "Volunteer experience",
    eyebrow: "Community",
    addLabel: "Add volunteer role",
    fields: [
      ["role", "Role"],
      ["organisation", "Organisation"],
      ["dates", "Dates"],
      ["description", "Description", "textarea"],
    ],
  },
  {
    key: "achievements",
    title: "Achievements and awards",
    eyebrow: "Highlights",
    addLabel: "Add achievement",
    fields: [
      ["title", "Achievement / award"],
      ["issuer", "Issued by"],
      ["date", "Date"],
      ["description", "Description", "textarea"],
    ],
  },
];

let profileState = {};

async function initProfile() {
  if (!requireAuth()) return;
  renderDynamicSections();
  bindProfileEvents();
  await loadProfile();
}

function renderDynamicSections() {
  const root = document.getElementById("dynamicSections");
  root.innerHTML = sectionConfigs.map(config => `
    <section class="profile-section glass-card" data-section="${config.key}">
      <div class="profile-section-head">
        <div>
          <span class="eyebrow">${escHtml(config.eyebrow)}</span>
          <h2>${escHtml(config.title)}</h2>
        </div>
        <button class="btn btn-ghost" type="button" data-add-row="${config.key}">${escHtml(config.addLabel)}</button>
      </div>
      <div class="repeat-list" id="${config.key}List"></div>
    </section>
  `).join("");

  sectionConfigs.forEach(config => {
    document.querySelector(`[data-add-row="${config.key}"]`)?.addEventListener("click", () => {
      profileState[config.key] = [...(profileState[config.key] || []), {}];
      renderSectionRows(config);
    });
  });
}

function bindProfileEvents() {
  document.getElementById("profileForm")?.addEventListener("submit", saveProfile);
  document.getElementById("resumeUpload")?.addEventListener("change", handleResumeUpload);
  document.getElementById("navAvatar")?.addEventListener("click", e => {
    e.stopPropagation();
    document.getElementById("avatarMenu")?.classList.toggle("open");
  });
  document.addEventListener("click", () => document.getElementById("avatarMenu")?.classList.remove("open"));
}

async function loadProfile() {
  try {
    profileState = await api.get("/profile/me");
    hydrateStaticFields(profileState);
    sectionConfigs.forEach(config => renderSectionRows(config));
    updateProfileSummary(profileState);
  } catch (err) {
    showToast(err.detail || "Could not load profile", "error");
  }
}

function hydrateStaticFields(profile) {
  const form = document.getElementById("profileForm");
  const directFields = [
    "avatar_url", "headline", "location", "bio", "phone", "linkedin_url", "github_url",
    "portfolio_url", "desired_job_title", "preferred_job_type", "preferred_work_style",
    "expected_salary_min", "expected_salary_max", "available_from", "resume_file_name", "resume_url",
  ];

  directFields.forEach(name => {
    const field = form.elements[name];
    if (field) field.value = profile[name] || "";
  });

  form.elements.open_to_work.checked = Boolean(profile.open_to_work);
  form.elements.available_immediately.checked = Boolean(profile.available_immediately);
  form.elements.resume_visible_to_recruiters.checked = Boolean(profile.resume_visible_to_recruiters);
  form.elements.preferred_locations.value = (profile.preferred_locations || []).join(", ");
  form.elements.industries.value = (profile.industries || []).join(", ");
  document.getElementById("profileEmail").value = profile.email || "";
}

function renderSectionRows(config) {
  const list = document.getElementById(`${config.key}List`);
  const items = profileState[config.key] || [];
  if (!items.length) {
    list.innerHTML = `<div class="empty-mini">No ${escHtml(config.title.toLowerCase())} added yet.</div>`;
    return;
  }

  list.innerHTML = items.map((item, index) => `
    <article class="repeat-row" data-row="${index}">
      <button class="row-remove" type="button" aria-label="Remove item" data-remove-row="${config.key}:${index}">Remove</button>
      <div class="form-grid">
        ${config.fields.map(([name, label, type]) => fieldHtml(config.key, index, name, label, type, item[name])).join("")}
      </div>
    </article>
  `).join("");

  list.querySelectorAll("[data-remove-row]").forEach(button => {
    button.addEventListener("click", () => {
      const [key, rawIndex] = button.dataset.removeRow.split(":");
      profileState[key].splice(Number(rawIndex), 1);
      renderSectionRows(config);
    });
  });
}

function fieldHtml(sectionKey, index, name, label, type, value) {
  const path = `${sectionKey}.${index}.${name}`;
  const safeValue = escAttr(value || "");
  if (type === "textarea") {
    return `<label>${escHtml(label)}<textarea data-profile-field="${path}" rows="3">${escHtml(value || "")}</textarea></label>`;
  }
  return `<label>${escHtml(label)}<input data-profile-field="${path}" value="${safeValue}" /></label>`;
}

async function saveProfile(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = collectProfilePayload(form);
  const button = form.querySelector("button[type=submit]");
  setLoading(button, true);

  try {
    profileState = await api.put("/profile/me", payload);
    hydrateStaticFields(profileState);
    sectionConfigs.forEach(config => renderSectionRows(config));
    updateProfileSummary(profileState);
    showToast("Profile saved", "success");
  } catch (err) {
    showToast(err.detail || "Could not save profile", "error");
  } finally {
    setLoading(button, false);
  }
}

function collectProfilePayload(form) {
  const payload = {
    avatar_url: clean(form.elements.avatar_url.value),
    headline: clean(form.elements.headline.value),
    location: clean(form.elements.location.value),
    bio: clean(form.elements.bio.value),
    open_to_work: form.elements.open_to_work.checked,
    phone: clean(form.elements.phone.value),
    linkedin_url: clean(form.elements.linkedin_url.value),
    github_url: clean(form.elements.github_url.value),
    portfolio_url: clean(form.elements.portfolio_url.value),
    desired_job_title: clean(form.elements.desired_job_title.value),
    preferred_job_type: clean(form.elements.preferred_job_type.value),
    preferred_work_style: clean(form.elements.preferred_work_style.value),
    preferred_locations: splitList(form.elements.preferred_locations.value),
    expected_salary_min: numberOrNull(form.elements.expected_salary_min.value),
    expected_salary_max: numberOrNull(form.elements.expected_salary_max.value),
    industries: splitList(form.elements.industries.value),
    available_from: clean(form.elements.available_from.value),
    available_immediately: form.elements.available_immediately.checked,
    resume_file_name: clean(form.elements.resume_file_name.value),
    resume_url: clean(form.elements.resume_url.value),
    resume_visible_to_recruiters: form.elements.resume_visible_to_recruiters.checked,
  };

  sectionConfigs.forEach(config => {
    payload[config.key] = collectSection(config);
  });

  return payload;
}

function collectSection(config) {
  const items = profileState[config.key] || [];
  return items.map((_, index) => {
    const entry = {};
    config.fields.forEach(([name]) => {
      entry[name] = clean(document.querySelector(`[data-profile-field="${config.key}.${index}.${name}"]`)?.value);
    });
    return entry;
  }).filter(item => Object.values(item).some(Boolean));
}

function handleResumeUpload(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  if (file.type !== "application/pdf") {
    showToast("Please upload a PDF resume.", "error");
    event.target.value = "";
    return;
  }

  const reader = new FileReader();
  reader.onload = () => {
    const form = document.getElementById("profileForm");
    form.elements.resume_file_name.value = file.name;
    form.elements.resume_url.value = reader.result;
    updateResumeDownload(reader.result, file.name);
    showToast("Resume attached. Save profile to keep it.", "success");
  };
  reader.readAsDataURL(file);
}

function updateProfileSummary(profile) {
  const initials = (profile.full_name || "NH").split(" ").map(part => part[0]).join("").slice(0, 2).toUpperCase();
  document.getElementById("profileAvatar").textContent = initials;
  document.getElementById("navInitials").textContent = initials;
  document.getElementById("profileName").textContent = profile.full_name || "Your profile";
  document.getElementById("profileHeadline").textContent = profile.headline || "Add a headline, skills, resume, and preferences so NextHire can personalize your search.";
  document.getElementById("navUserName").textContent = profile.full_name || "";
  document.getElementById("navUserEmail").textContent = profile.email || "";
  document.getElementById("openBanner").classList.toggle("visible", Boolean(profile.open_to_work));
  document.getElementById("completionPercent").textContent = `${profile.completeness || 0}%`;
  document.getElementById("completionBar").style.width = `${profile.completeness || 0}%`;
  document.getElementById("missingChecklist").innerHTML = (profile.missing_items || []).length
    ? profile.missing_items.map(item => `<div>${escHtml(item)}</div>`).join("")
    : `<div>Everything important is complete.</div>`;
  updateResumeDownload(profile.resume_url, profile.resume_file_name);
}

function updateResumeDownload(url, name) {
  const link = document.getElementById("resumeDownload");
  if (!url) {
    link.classList.add("hidden");
    return;
  }
  link.href = url;
  link.download = name || "resume.pdf";
  link.classList.remove("hidden");
}

function splitList(value) {
  return String(value || "").split(",").map(item => item.trim()).filter(Boolean);
}

function numberOrNull(value) {
  const number = Number(value);
  return Number.isFinite(number) && value !== "" ? number : null;
}

function clean(value) {
  const trimmed = String(value || "").trim();
  return trimmed || null;
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
