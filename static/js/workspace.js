(() => {
  if (window.strideWorkspaceEvents) return;
  window.strideWorkspaceEvents = true;

  const showRequestError = (event) => {
    if (!event.detail.elt?.closest(".app-shell")) return;
    const message = document.getElementById("workspace-request-error");
    if (message) message.hidden = false;
  };
  document.addEventListener("htmx:responseError", showRequestError);
  document.addEventListener("htmx:sendError", showRequestError);
  document.addEventListener("click", (event) => {
    const drawer = document.getElementById("workspace-navigation");
    if (event.target.closest("[data-open-navigation]") && drawer && !drawer.open) {
      drawer.showModal();
      drawer.querySelector("[data-close-navigation]").focus();
    }
    if (drawer?.open) {
      const rect = drawer.getBoundingClientRect();
      const backdrop = event.target === drawer && (
        event.clientX < rect.left || event.clientX > rect.right ||
        event.clientY < rect.top || event.clientY > rect.bottom
      );
      if (
        backdrop || event.target.closest("[data-close-navigation]") ||
        (event.target.closest("a") && drawer.contains(event.target))
      ) drawer.close();
    }
    if (event.target.closest("[data-dismiss-request-error]")) {
      document.getElementById("workspace-request-error").hidden = true;
    }
  });
  document.addEventListener("htmx:beforeSwap", () => {
    document.getElementById("workspace-navigation")?.close();
  });
  window.matchMedia("(min-width: 761px)").addEventListener("change", (event) => {
    if (event.matches) document.getElementById("workspace-navigation")?.close();
  });
})();
