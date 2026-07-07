function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function userInitials(fullName) {
  return String(fullName || "User")
    .split(" ")
    .map(part => part[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

function hydrateCurrentUserNav(user, options = {}) {
  const fullName = user?.full_name || "User";
  setText("navInitials", userInitials(fullName));
  setText("navUserName", fullName);
  setText("navUserEmail", user?.email || "");

  if (options.greetingId) {
    setText(options.greetingId, `Welcome, ${fullName.split(" ")[0]}`);
  }
}

async function loadCurrentUserNav(options = {}) {
  try {
    const user = await api.get("/auth/me");
    hydrateCurrentUserNav(user, options);
    return user;
  } catch (err) {
    if (err.status === 401) logout();
    return null;
  }
}
