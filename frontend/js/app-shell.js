(function () {
  async function initAppShell() {
    if (typeof api === "undefined" || typeof Auth === "undefined") return;
    if (!Auth.isLoggedIn()) {
      applyRoleNavigation(null);
      return;
    }
    try {
      const user = await api.get("/auth/me");
      applyRoleNavigation(user);
      await applyProfileAvatar(user);
      renderNotificationBell();
      await refreshNotifications();
    } catch (_) {
      applyRoleNavigation(null);
    }
  }

  function applyRoleNavigation(user) {
    const currentPage = currentPageName();
    const navCenter = document.querySelector(".app-nav .nav-center");
    const actions = document.querySelector(".app-nav .nav-actions");

    document.querySelectorAll(".app-nav .logo").forEach(link => {
      link.classList.remove("hidden");
      link.setAttribute("href", user ? "dashboard.html" : "index.html");
    });

    if (navCenter) navCenter.innerHTML = user
      ? userNavLinks(user, currentPage)
      : publicNavLinks(currentPage);

    ensureAvatarMenu(user);
    const avatarName = document.getElementById("navUserName");
    const avatarEmail = document.getElementById("navUserEmail");
    const initials = document.getElementById("navInitials");
    document.getElementById("navAvatar")?.classList.toggle("hidden", !user);

    document.getElementById("publicNavLinks")?.remove();
    if (actions && !user) {
      actions.insertAdjacentHTML("beforeend", `
        <div class="public-nav-links" id="publicNavLinks">
          <a href="login.html">Login</a>
          <a class="nav-cta" href="register.html">Try for free</a>
        </div>
      `);
    }
    if (avatarName && user) avatarName.textContent = user.company_name || user.full_name || "";
    if (avatarEmail && user) avatarEmail.textContent = user.email || "";
    if (initials && user) initials.textContent = (user.company_name || user.full_name || "NH")
      .split(" ")
      .map(part => part[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  }

  function publicNavLinks(currentPage) {
    return [
      navLink("index.html", "Home", currentPage),
      navLink("about.html", "About", currentPage),
      navLink("search.html", "Jobs", currentPage),
      navLink("index.html#categories", "Categories", currentPage),
      navLink("index.html#companies", "Companies", currentPage),
    ].join("");
  }

  function userNavLinks(user, currentPage) {
    const links = [
      navLink("dashboard.html", "Dashboard", currentPage),
      navLink("search.html", "Search", currentPage),
      navLink("jobs.html", "Board", currentPage),
      navLink("profile.html", "Profile", currentPage),
    ];
    if (user?.account_type === "company") {
      links.push(navLink(
        "employer.html",
        user.company_status === "approved" && user.company_verified ? "Post jobs" : "Company pending",
        currentPage
      ));
    }
    if (user?.is_admin) links.push(navLink("admin.html", "Admin", currentPage));
    return links.join("");
  }

  function navLink(href, label, currentPage) {
    const page = href.split("#")[0];
    const active = page === currentPage ? " class=\"active\"" : "";
    return `<a href="${href}"${active}>${label}</a>`;
  }

  function currentPageName() {
    const page = window.location.pathname.split("/").pop();
    return page || "index.html";
  }

  function ensureAvatarMenu(user) {
    const actions = document.querySelector(".app-nav .nav-actions");
    if (!actions || !user) {
      document.getElementById("navAvatar")?.classList.add("hidden");
      return;
    }
    let avatar = document.getElementById("navAvatar");
    if (!avatar) {
      actions.insertAdjacentHTML("beforeend", `
        <div class="nav-avatar" id="navAvatar">
          <span id="navInitials">NH</span>
          <div class="nav-avatar-menu" id="avatarMenu"></div>
        </div>
      `);
      avatar = document.getElementById("navAvatar");
    }
    avatar.innerHTML = `
        <span id="navInitials">NH</span>
        <div class="nav-avatar-menu" id="avatarMenu">
          <div class="avatar-menu-head">
            <div id="navUserName"></div>
            <small id="navUserEmail"></small>
          </div>
          <a href="dashboard.html">Dashboard</a>
          <a href="search.html">Search jobs</a>
          <a href="jobs.html">My board</a>
          <a href="profile.html">Profile</a>
          ${user?.account_type === "company" ? `<a href="employer.html">Company hiring</a>` : ""}
          ${user?.is_admin ? `<a href="admin.html">Admin console</a>` : ""}
          <button class="menu-danger" onclick="logout()">Sign out</button>
        </div>
    `;
    if (avatar.dataset.bound === "true") return;
    avatar.dataset.bound = "true";
    avatar.addEventListener("click", event => {
      event.stopPropagation();
      document.getElementById("avatarMenu")?.classList.toggle("open");
    });
    document.addEventListener("click", () => document.getElementById("avatarMenu")?.classList.remove("open"));
  }

  async function applyProfileAvatar(user) {
    const avatar = document.getElementById("navAvatar");
    const initials = document.getElementById("navInitials");
    if (!avatar || !user || user.account_type === "company") return;
    try {
      const profile = await api.get("/profile/me");
      if (!profile?.avatar_url) return;
      avatar.classList.add("has-avatar-image");
      avatar.style.backgroundImage = `url("${cssUrl(profile.avatar_url)}")`;
      if (initials) initials.textContent = "";
    } catch (_) { }
  }

  function renderNotificationBell() {
    const actions = document.querySelector(".app-nav .nav-actions");
    if (!actions || document.getElementById("notificationBell")) return;
    actions.insertAdjacentHTML("afterbegin", `
      <div class="notification-wrap">
        <button class="notification-bell" id="notificationBell" type="button" aria-label="Notifications">
          <span class="bell-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M15 17h5l-1.4-1.4A2 2 0 0 1 18 14.2V11a6 6 0 1 0-12 0v3.2c0 .5-.2 1-.6 1.4L4 17h5"/>
              <path d="M10 21h4"/>
            </svg>
          </span>
          <span class="notification-count hidden" id="notificationCount">0</span>
        </button>
        <div class="notification-panel glass-card" id="notificationPanel">
          <div class="notification-head">
            <strong>Notifications</strong>
            <button type="button" id="markNotificationsRead">Mark read</button>
          </div>
          <div id="notificationList" class="notification-list"></div>
        </div>
      </div>
    `);
    document.getElementById("notificationBell")?.addEventListener("click", event => {
      event.stopPropagation();
      document.getElementById("notificationPanel")?.classList.toggle("open");
    });
    document.getElementById("markNotificationsRead")?.addEventListener("click", async () => {
      await api.patch("/notifications/read-all", {});
      await refreshNotifications();
    });
    document.addEventListener("click", () => document.getElementById("notificationPanel")?.classList.remove("open"));
  }

  function renderAppFooter() {
    if (document.querySelector(".app-footer") || document.body.classList.contains("marketing-page")) return;
    const accountLinks = Auth.isLoggedIn()
      ? `<a href="profile.html">Profile</a>`
      : `<a href="login.html">Login</a><a href="register.html">Try for free</a>`;
    document.body.insertAdjacentHTML("beforeend", `
      <footer class="app-footer">
        <div class="footer-main">
          <div class="footer-brand">
            <a class="footer-logo" href="index.html">NextHire</a>
            <p>Search roles, apply with a complete profile, track your pipeline, and help verified companies review candidates in one calm workspace.</p>
          </div>
          <nav class="footer-column" aria-label="Product links">
            <strong>Product</strong>
            <a href="search.html">Job search</a>
            <a href="jobs.html">Saved jobs</a>
            <a href="dashboard.html">Dashboard</a>
          </nav>
          <nav class="footer-column" aria-label="Workspace links">
            <strong>Workspaces</strong>
            <a href="profile.html">Candidate profile</a>
            <a href="employer.html">Company hiring</a>
            <a href="admin.html">Admin console</a>
          </nav>
          <nav class="footer-column" aria-label="Company links">
            <strong>Company</strong>
            <a href="about.html">About</a>
            ${accountLinks}
          </nav>
        </div>
        <div class="footer-bottom">
          <span>2026 NextHire. Built for modern hiring teams.</span>
          <span>support@nexthire.local</span>
        </div>
      </footer>
    `);
  }

  async function refreshNotifications() {
    const notes = await api.get("/notifications");
    const unread = notes.filter(note => !note.is_read).length;
    const count = document.getElementById("notificationCount");
    if (count) {
      count.textContent = unread;
      count.classList.toggle("hidden", unread === 0);
    }
    const list = document.getElementById("notificationList");
    if (list) {
      list.innerHTML = notes.length ? notes.slice(0, 8).map(note => `
        <button class="notification-item ${note.is_read ? "" : "unread"}" type="button" data-note-id="${note.id}">
          <strong>${escapeHtml(note.title)}</strong>
          <span>${escapeHtml(note.message)}</span>
        </button>
      `).join("") : `<div class="chart-empty">No notifications yet.</div>`;
      list.querySelectorAll("[data-note-id]").forEach(item => {
        item.addEventListener("click", async () => {
          await api.patch(`/notifications/${item.dataset.noteId}/read`, {});
          await refreshNotifications();
        });
      });
    }
  }

  function escapeHtml(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function cssUrl(value) {
    return String(value || "").replace(/["\\\n\r]/g, "");
  }

  window.initAppShell = initAppShell;
  const originalInitAppShell = window.initAppShell;
  window.initAppShell = async function () {
    await originalInitAppShell();
    renderAppFooter();
  };
})();
