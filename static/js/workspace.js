(() => {
  if (window.strideWorkspaceEvents) return;
  window.strideWorkspaceEvents = true;

  const showRequestError = (event) => {
    if (!event.detail.elt?.closest(".app-shell")) return;
    const message = event.detail.elt.closest("#task-dialog")?.querySelector("[data-task-request-error]") || document.getElementById("workspace-request-error");
    if (message) {
      message.hidden = false;
      if (message.hasAttribute("data-task-request-error")) message.focus();
    }
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
    const taskDialog = document.getElementById("task-dialog");
    if (taskDialog?.open) {
      const rect = taskDialog.getBoundingClientRect();
      const backdrop = event.target === taskDialog && (
        event.clientX < rect.left || event.clientX > rect.right ||
        event.clientY < rect.top || event.clientY > rect.bottom
      );
      if (backdrop || event.target.closest("[data-close-task-dialog]")) taskDialog.close();
    }
  });
  document.addEventListener("htmx:afterSettle", (event) => {
    if (event.detail.target.id !== "task-dialog-content") return;
    const dialog = document.getElementById("task-dialog");
    if (!dialog?.querySelector("#task-dialog-title")) return;
    if (!dialog.open) dialog.showModal();
    const focus = dialog.querySelector('[aria-invalid="true"]') ||
      dialog.querySelector('[autofocus], [data-task-initial-focus]');
    (focus || dialog.querySelector("[data-close-task-dialog]"))?.focus();
  });
  document.addEventListener("taskSaved", (event) => {
    document.getElementById("task-dialog")?.close();
    const id = Number(event.detail.task_id);
    const task = id > 0 ? document.querySelector(`[data-task-id="${id}"]`) : null;
    (task || document.getElementById("new-task"))?.focus();
    const status = document.getElementById("task-live-status");
    if (status) status.textContent = event.detail.message;
  });
  document.addEventListener("htmx:beforeSwap", () => {
    document.getElementById("workspace-navigation")?.close();
  });
  window.matchMedia("(min-width: 761px)").addEventListener("change", (event) => {
    if (event.matches) document.getElementById("workspace-navigation")?.close();
  });
})();
