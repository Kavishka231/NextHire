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
      renderNotificationBell();
      await refreshNotifications();
    } catch (_) {
      applyRoleNavigation(null);
    }
  }

  function applyRoleNavigation(user) {
    document.querySelectorAll('a[href="/admin.html"]').forEach(link => {
      link.classList.toggle("hidden", !user?.is_admin);
    });

    document.querySelectorAll('a[href="/employer.html"]').forEach(link => {
      if (user?.account_type === "company") {
        link.classList.remove("hidden");
        link.textContent = user.company_status === "approved" && user.company_verified
          ? "Post jobs"
          : "Company pending";
      } else {
        link.classList.add("hidden");
      }
    });

    const avatarName = document.getElementById("navUserName");
    const avatarEmail = document.getElementById("navUserEmail");
    const initials = document.getElementById("navInitials");
    if (avatarName && user) avatarName.textContent = user.company_name || user.full_name || "";
    if (avatarEmail && user) avatarEmail.textContent = user.email || "";
    if (initials && user) initials.textContent = (user.company_name || user.full_name || "NH")
      .split(" ")
      .map(part => part[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  }

  function renderNotificationBell() {
    const actions = document.querySelector(".app-nav .nav-actions");
    if (!actions || document.getElementById("notificationBell")) return;
    actions.insertAdjacentHTML("afterbegin", `
      <div class="notification-wrap">
        <button class="notification-bell" id="notificationBell" type="button" aria-label="Notifications">
          <span class="bell-icon">!</span>
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

  window.initAppShell = initAppShell;
})();
