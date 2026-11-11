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
    if (event.target.closest("[data-dismiss-request-error]")) {
      document.getElementById("workspace-request-error").hidden = true;
    }
  });
})();
