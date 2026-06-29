async function initDashboard() {
  if (!requireAuth()) return;
  await Promise.all([loadDashboardUser(), loadStats()]);
}

async function loadDashboardUser() {
  try {
    const user = await api.get("/auth/me");
    const fullName = user.full_name || "User";
    const initials = fullName.split(" ").map(part => part[0]).join("").toUpperCase().slice(0, 2);

    setText("navInitials", initials);
    setText("navUserName", fullName);
    setText("navUserEmail", user.email);
    setText("heroGreeting", `Welcome, ${fullName.split(" ")[0]}`);
  } catch (err) {
    if (err.status === 401) logout();
  }
}

async function loadStats() {
  try {
    const stats = await api.get("/stats");
    const total = stats.total_saved + stats.total_applied + stats.total_interviews + stats.total_offers + stats.total_rejected;

    renderKpi("kpiTotal", "Tracked", total, "Total opportunities");
    renderKpi("kpiApplied", "Applied", stats.total_applied, "Applications sent");
    renderKpi("kpiInterviews", "Interviews", stats.total_interviews, "Active conversations");
    renderKpi("kpiOffers", "Offers", stats.total_offers, "Wins in progress");
    renderKpi("kpiResponse", "Response", `${stats.response_rate}%`, "Interview response rate");
    renderKpi("kpiOfferRate", "Offer rate", `${stats.offer_rate}%`, "Applied to offer");

    renderDonut(stats.status_counts || []);
    renderWeekly(stats.weekly_activity || []);
    renderCompanies(stats.top_companies || []);
    renderSalary(stats.avg_salary_min, stats.avg_salary_max);
    renderActivity(stats.status_counts || []);
  } catch (err) {
    if (err.status === 401) logout();
    console.error(err);
  }
}

function renderKpi(id, label, value, sub) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = "kpi-card glass-card";
  el.innerHTML = `<span>${label}</span><strong>${value}</strong><small>${sub}</small>`;
}

function renderDonut(rows) {
  const el = document.getElementById("funnelChart");
  if (!el) return;
  const total = rows.reduce((sum, row) => sum + row.count, 0);
  if (!total) {
    el.innerHTML = `<div class="chart-empty">Save and track jobs to see your pipeline.</div>`;
    return;
  }

  let offset = 0;
  const stops = rows.map((row) => {
    const start = offset;
    offset += (row.count / total) * 100;
    return `${row.color} ${start}% ${offset}%`;
  }).join(", ");

  el.innerHTML = `
    <div class="donut-wrap">
      <div class="donut" style="background:conic-gradient(${stops})"><span>${total}</span></div>
      <div class="legend">${rows.map(row => `<span><i style="background:${row.color}"></i>${row.label} ${row.count}</span>`).join("")}</div>
    </div>`;
}

function renderWeekly(rows) {
  const el = document.getElementById("weeklyChart");
  if (!el) return;
  const max = Math.max(1, ...rows.map(row => row.count));
  el.innerHTML = `<div class="bar-chart">${rows.map(row => `
    <div class="bar-item">
      <div class="bar-track"><span style="height:${Math.max(8, (row.count / max) * 100)}%"></span></div>
      <small>${row.week}</small>
    </div>`).join("")}</div>`;
}

function renderCompanies(rows) {
  const el = document.getElementById("topCompanies");
  if (!el) return;
  if (!rows.length) {
    el.innerHTML = `<div class="chart-empty">No company data yet.</div>`;
    return;
  }
  el.innerHTML = rows.map(row => `<div class="company-row"><span>${esc(row.company)}</span><strong>${row.count}</strong></div>`).join("");
}

function renderSalary(min, max) {
  const el = document.getElementById("salaryCard");
  if (!el) return;
  if (!min && !max) {
    el.innerHTML = `<div class="chart-empty">Save jobs with salary info.</div>`;
    return;
  }
  el.innerHTML = `<div class="salary-range"><strong>${formatMoney(min)}</strong><span>to</span><strong>${formatMoney(max)}</strong></div>`;
}

function renderActivity(rows) {
  const el = document.getElementById("recentActivity");
  if (!el) return;
  el.innerHTML = rows.map(row => `<div class="activity-row"><span>${row.label}</span><strong>${row.count}</strong></div>`).join("");
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function formatMoney(value) {
  if (!value) return "N/A";
  return value >= 1000 ? `$${Math.round(value / 1000)}k` : `$${value}`;
}

function esc(str) {
  return String(str || "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
