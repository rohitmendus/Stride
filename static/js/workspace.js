(() => {
  if (window.strideWorkspaceEvents) return;
  window.strideWorkspaceEvents = true;

  let toastTimer;
  let savedTaskFocus = null;
  let memberFocus = false;
  window.strideNotify = (message, announcement = message, saved = true) => {
    const toast = document.getElementById("workspace-toast");
    if (toast) {
      clearTimeout(toastTimer);
      toast.textContent = message;
      toast.hidden = false;
      toastTimer = setTimeout(() => { toast.hidden = true; }, 3500);
    }
    const live = document.getElementById("task-live-status");
    if (live) live.textContent = announcement;
    const status = document.getElementById("save-status");
    if (status) status.textContent = saved ? "All changes saved" : "Change not confirmed";
  };

  const showFlashMessages = () => {
    const messages = document.querySelector(".site-messages");
    const message = messages?.querySelector(".site-message:last-child");
    if (!message) return;
    window.strideNotify(message.textContent.trim());
    messages.remove();
  };
  document.addEventListener("htmx:afterSettle", showFlashMessages);

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
    document.querySelectorAll(".project-options[open]").forEach((menu) => {
      if (!menu.contains(event.target) || event.target.closest("a")) menu.open = false;
    });
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
    if (event.detail.target.id === "project-members") {
      const invalid = document.querySelector('#project-members [aria-invalid="true"]');
      if (invalid || memberFocus) (invalid || document.getElementById("members-heading"))?.focus();
      memberFocus = false;
    }
    if (savedTaskFocus !== null) {
      const task = document.querySelector(`[data-task-id="${savedTaskFocus}"]`);
      (task || document.getElementById("new-task") || document.getElementById("project-board"))?.focus();
      savedTaskFocus = null;
    }
    if (event.detail.target.id !== "task-dialog-content") return;
    const dialog = document.getElementById("task-dialog");
    if (!dialog?.querySelector("#task-dialog-title")) return;
    if (!dialog.open) dialog.showModal();
    const focus = dialog.querySelector('[aria-invalid="true"]') ||
      dialog.querySelector('[autofocus], [data-task-initial-focus]');
    (focus || dialog.querySelector("[data-close-task-dialog]"))?.focus();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || document.querySelector("dialog[open]")) return;
    const menu = document.querySelector(".project-options[open]");
    if (menu) { menu.open = false; menu.querySelector("summary").focus(); }
  });
  document.addEventListener("taskSaved", (event) => {
    document.getElementById("task-dialog")?.close();
    savedTaskFocus = Number(event.detail.task_id);
    window.strideNotify(event.detail.message);
  });
  document.addEventListener("taskMoved", (event) => {
    window.strideNotify(event.detail.message, event.detail.announcement);
  });
  document.addEventListener("memberSaved", (event) => {
    memberFocus = true;
    window.strideNotify(event.detail.message);
  });
  document.addEventListener("htmx:beforeSwap", () => {
    document.getElementById("workspace-navigation")?.close();
  });
  window.matchMedia("(min-width: 761px)").addEventListener("change", (event) => {
    if (event.matches) document.getElementById("workspace-navigation")?.close();
  });
  showFlashMessages();
})();
