(function () {
  const root = document.documentElement;
  const storageKey = "theme";

  function getInitialTheme() {
    const saved = localStorage.getItem(storageKey);
    if (saved === "dark" || saved === "light") return saved;
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function applyTheme(theme) {
    const next = theme === "dark" ? "dark" : "light";
    root.dataset.theme = next;
    localStorage.setItem(storageKey, next);
    document.querySelectorAll("[data-theme-toggle], #themeToggle").forEach((button) => {
      button.removeAttribute("hidden");
      button.style.removeProperty("display");
      button.setAttribute("aria-pressed", String(next === "dark"));
      button.setAttribute("title", next === "dark" ? "Switch to light mode" : "Switch to dark mode");
    });
  }

  applyTheme(getInitialTheme());

  window.initThemeToggle = function initThemeToggle() {
    document.querySelectorAll("[data-theme-toggle], #themeToggle").forEach((button) => {
      if (button.dataset.themeBound === "true") return;
      button.dataset.themeBound = "true";
      button.addEventListener("click", () => {
        applyTheme(root.dataset.theme === "dark" ? "light" : "dark");
      });
    });
  };
})();
