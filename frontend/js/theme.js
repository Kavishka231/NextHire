(function () {
  const root = document.documentElement;
  const stored = localStorage.getItem("theme");
  const preferred = window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches
    ? "light"
    : "dark";

  root.dataset.theme = stored || preferred;

  window.initThemeToggle = function initThemeToggle() {
    document.querySelectorAll("[data-theme-toggle], #themeToggle").forEach((button) => {
      if (button.dataset.themeBound === "true") return;
      button.dataset.themeBound = "true";
      button.addEventListener("click", () => {
        const next = root.dataset.theme === "light" ? "dark" : "light";
        root.dataset.theme = next;
        localStorage.setItem("theme", next);
      });
    });
  };
})();
