async function initDashboard() {
  if (!requireAuth()) return;
  await Promise.all([loadDashboardUser(), loadStats()]);
}

async function loadDashboardUser() {
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

    const greeting = document.getElementById("heroGreeting");
    if (greeting) greeting.textContent = `Welcome, ${fullName.split(" ")[0]}`;
  } catch (err) {
    if (err.status === 401) logout();
  }
}

async function loadStats() {
  try {
    const stats = await api.get("/stats");
    renderKpi("kpiTotal", "Tracked", stats.total_saved + stats.total_applied + stats.total_interviews + stats.total_offers + stats.total_rejected);
    renderKpi("kpiApplied", "Applied", stats.total_applied);
    renderKpi("kpiInterviews", "Interviews", stats.total_interviews);
    renderKpi("kpiOffers", "Offers", stats.total_offers);
    renderKpi("kpiResponse", "Response rate", `${stats.response_rate}%`);
    renderKpi("kpiOfferRate", "Offer rate", `${stats.offer_rate}%`);
  } catch (err) {
    if (err.status === 401) logout();
    console.error(err);
  }
}

function renderKpi(id, label, value) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = "kpi-card";
  el.innerHTML = `<div class="kpi-label">${label}</div><div class="kpi-value">${value}</div>`;
}
