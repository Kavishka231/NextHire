const { test, expect } = require("@playwright/test");

const candidate = {
  id: 1, email: "candidate@example.com", full_name: "Casey Candidate",
  account_type: "candidate", is_admin: false, admin_role: "none",
};
const employer = {
  id: 2, email: "employer@example.com", full_name: "Erin Employer",
  account_type: "company", company_name: "Acme Labs", company_status: "approved",
  company_verified: true, company_website: "https://acme.example",
  company_description: "Product engineering company", is_admin: false, admin_role: "none",
};
const admin = {
  id: 3, email: "admin@example.com", full_name: "Alex Admin",
  account_type: "candidate", is_admin: true, admin_role: "super_admin",
};
const pythonJob = {
  id: 10, external_id: "python-10", title: "Python Engineer", company: "Acme Labs",
  location: "Remote", description: "Build reliable Python services", salary_min: 70000,
  salary_max: 90000, category: "IT Jobs", contract_type: "permanent",
  contract_time: "full_time", created: "2026-08-01T00:00:00Z", url: "https://jobs.example/10",
};

function pageData(items) {
  return { items, total: items.length, page: 1, page_size: 25 };
}

async function mockApi(page, initialRole = "candidate") {
  const state = {
    role: initialRole,
    saved: [{ id: 21, status: "saved", job: pythonJob }],
    notes: [], jobs: [], applicationStatus: "submitted", requests: [],
  };
  const users = { candidate, employer, admin };
  await page.route("**/api/v1/**", async route => {
    const req = route.request();
    const url = new URL(req.url());
    const path = url.pathname.replace("/api/v1", "");
    const method = req.method();
    let body = {};
    try { body = req.postDataJSON() || {}; } catch (_) { }
    state.requests.push({ method, path, body });
    const json = (value, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(value) });

    if (path === "/auth/refresh") return state.role === "none" ? json({ detail: "Not authenticated" }, 401) : json({ access_token: `${state.role}-token` });
    if (path === "/auth/register") return json({ id: 99, ...body }, 201);
    if (path === "/auth/login") {
      state.role = body.email.startsWith("admin") ? "admin" : body.email.startsWith("employer") ? "employer" : "candidate";
      return json({ access_token: `${state.role}-token` });
    }
    if (path === "/auth/me") return state.role === "none" ? json({ detail: "Not authenticated" }, 401) : json(users[state.role]);
    if (path === "/profile/me") return json({ user_id: 1, email: candidate.email, full_name: candidate.full_name, headline: "Python Developer", completion_percent: 80, skills: [], education: [], experience: [], projects: [], certifications: [], languages: [] });
    if (path === "/notifications") return json([]);
    if (path === "/search/categories") return json([{ tag: "it-jobs", label: "IT Jobs" }]);
    if (path === "/search/jobs") return json({ total: 1, page: 1, results_per_page: 20, jobs: [pythonJob] });
    if (path === "/saved-jobs" && method === "POST") return json(state.saved[0], 201);
    if (path === "/saved-jobs" && method === "GET") return json(pageData(state.saved));
    if (/^\/saved-jobs\/\d+\/status$/.test(path)) { state.saved[0].status = body.status; return json(state.saved[0]); }
    if (/^\/notes\/job\/\d+$/.test(path)) return json(pageData(state.notes));
    if (path === "/notes" && method === "POST") { state.notes.push({ id: 1, content: body.content }); return json(state.notes[0], 201); }
    if (path === "/stats") return json({ total_saved: 1, total_applied: 1, total_interviews: 1, total_offers: 0, total_rejected: 0, response_rate: 50, offer_rate: 0, status_counts: [{ label: "Applied", count: 1, color: "#2563eb" }], weekly_activity: [{ week: "This week", count: 2 }], top_companies: [{ company: "Acme Labs", count: 1 }], avg_salary_min: 70000, avg_salary_max: 90000 });
    if (path === "/jobs/company/mine") return json(pageData(state.jobs));
    if (path === "/applications/company") return json(pageData([{ id: 31, status: state.applicationStatus, applicant_name: "Casey Candidate", applicant_email: candidate.email, job_title: "Python Engineer", created_at: "2026-08-01T00:00:00Z" }]));
    if (path === "/company/me" && method === "PUT") return json({ ...employer, ...body });
    if (path === "/jobs/company" && method === "POST") { const job = { id: 44, external_id: "company-44", ...body }; state.jobs.push(job); return json(job, 201); }
    if (/^\/applications\/\d+\/status$/.test(path)) { state.applicationStatus = body.status; return json({ id: 31, status: body.status }); }
    if (path === "/admin/summary") return json({ total_users: 3, new_users_week: 1, total_jobs: 2, total_searches: 4, total_saved: 1, total_applications: 1 });
    if (path === "/admin/users") return json(pageData([{ ...candidate, join_date: "2026-08-01", saved_jobs: 1, applied_jobs: 1, is_active: true, is_verified: true }]));
    if (path === "/admin/companies/pending") return json([{ ...employer, id: 2, company_status: "pending" }]);
    if (path === "/admin/jobs") return method === "GET" ? json(pageData([{ ...pythonJob, saved_count: 1, application_count: 1, is_featured: false }])) : json({ id: 55, ...body }, 201);
    if (path === "/admin/moderation/notes") return json(pageData([{ id: 7, user_email: candidate.email, content: "Review this note" }]));
    if (path === "/admin/moderation/profiles") return json([{ user: candidate, profile: { id: 8, headline: "Python Developer" } }]);
    if (path === "/admin/analytics") return json({ conversion_funnel: { saved: 1, applied: 1 }, top_keywords: [], top_locations: [], top_categories: [] });
    if (path === "/admin/email/reminder-preview") return json({ subject: "Reminder", html: "Application reminder" });
    if (path === "/admin/health") return json({ database: "ok", redis: "ok" });
    if (/^\/admin\/(companies|users|moderation)/.test(path)) return json({ ok: true });
    return json({ detail: `Unhandled mock ${method} ${path}` }, 404);
  });
  return state;
}

test("candidate registers an account", async ({ page }) => {
  const state = await mockApi(page, "none");
  await page.goto("/register.html");
  await page.locator("#name").fill("Casey Candidate");
  await page.locator("#email").fill(candidate.email);
  await page.locator("#password").fill("StrongPass123!");
  await page.locator("#confirmPassword").fill("StrongPass123!");
  await page.getByRole("button", { name: "Register" }).click();
  await expect(page.locator("#alertBox")).toContainText("Account created");
  expect(state.requests.some(r => r.path === "/auth/register" && r.body.account_type === "candidate")).toBeTruthy();
});

test("candidate logs in and reaches the dashboard", async ({ page }) => {
  await mockApi(page, "none");
  await page.goto("/login.html");
  await page.locator("#email").fill(candidate.email);
  await page.locator("#password").fill("StrongPass123!");
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/dashboard\.html/);
  await expect(page.locator("#heroGreeting")).toContainText("Casey");
});

test("candidate searches for Python jobs and saves one", async ({ page }) => {
  const state = await mockApi(page);
  await page.goto("/search.html");
  await page.locator("#searchKeywords").fill("Python");
  await page.locator("#heroSearchForm").press("Enter");
  await expect(page.getByText("Python Engineer")).toBeVisible();
  await page.locator(".job-card-save").click();
  await expect.poll(() => state.requests.filter(r => r.path === "/saved-jobs" && r.method === "POST").length).toBe(1);
});

test("candidate changes a saved-job status", async ({ page }) => {
  const state = await mockApi(page);
  await page.goto("/jobs.html");
  await page.locator("[data-status-select]").selectOption("applied");
  await expect.poll(() => state.saved[0].status).toBe("applied");
  await expect(page.locator("[data-status-select]")).toHaveValue("applied");
});

test("candidate adds a note to a saved job", async ({ page }) => {
  const state = await mockApi(page);
  await page.goto("/jobs.html");
  await page.getByRole("button", { name: "Notes", exact: true }).click();
  await page.locator("#noteInput").fill("Prepare system-design examples");
  await page.locator("#noteSubmitBtn").click();
  await expect(page.locator("#notesList")).toContainText("Prepare system-design examples");
  expect(state.notes).toHaveLength(1);
});

test("candidate views pipeline statistics on the dashboard", async ({ page }) => {
  await mockApi(page);
  await page.goto("/dashboard.html");
  await expect(page.locator("#kpiApplied")).toContainText("Applied");
  await expect(page.locator("#topCompanies")).toContainText("Acme Labs");
});

test("employer updates the company profile", async ({ page }) => {
  const state = await mockApi(page, "employer");
  await page.goto("/employer.html");
  await page.locator('[name="company_description"]').first().fill("Updated product engineering company");
  await page.getByRole("button", { name: "Save company details" }).click();
  await expect.poll(() => state.requests.some(r => r.path === "/company/me" && r.method === "PUT")).toBeTruthy();
});

test("employer publishes a job and sees it in owned posts", async ({ page }) => {
  await mockApi(page, "employer");
  await page.goto("/employer.html");
  const form = page.locator("#companyJobForm");
  await form.locator('[name="title"]').fill("Platform Engineer");
  await form.locator('[name="description"]').fill("Build the hiring platform");
  await form.getByRole("button", { name: "Publish job" }).click();
  await expect(page.locator("#companyJobsList")).toContainText("Platform Engineer");
});

test("employer reviews applications and updates status", async ({ page }) => {
  const state = await mockApi(page, "employer");
  await page.goto("/employer.html");
  await expect(page.locator("#companyApplicationsList")).toContainText("Casey Candidate");
  await page.locator("#companyApplicationsList select").selectOption("reviewing");
  await expect.poll(() => state.applicationStatus).toBe("reviewing");
});

test("admin opens dashboard and performs moderation/security actions", async ({ page }) => {
  const state = await mockApi(page, "admin");
  await page.goto("/admin.html");
  await expect(page.locator("#adminSummary")).toContainText("Users");
  await expect(page.locator("#adminNotes")).toContainText("Review this note");
  await page.getByRole("button", { name: "Approve" }).click();
  await page.getByRole("button", { name: "Deactivate" }).click();
  await expect.poll(() => state.requests.filter(r => r.method === "PATCH" && r.path.startsWith("/admin/")).length).toBeGreaterThanOrEqual(2);
});

test("unauthenticated visitor is redirected away from a protected page", async ({ page }) => {
  await mockApi(page, "none");
  await page.goto("/jobs.html");
  await expect(page).toHaveURL(/login\.html/);
  await expect(page.getByRole("heading", { name: "Login to NextHire" })).toBeVisible();
});
