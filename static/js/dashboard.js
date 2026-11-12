(() => {
  if (window.strideDashboardEvents) return;
  window.strideDashboardEvents = true;
  const isRefresh = (event) => event.detail.target?.id === 'dashboard-content';
  const showStale = (event) => {
    if (!isRefresh(event)) return;
    const status = document.querySelector('[data-dashboard-status]');
    if (status) {
      status.textContent = 'Unable to refresh. Showing the last update.';
      status.classList.add('is-stale');
    }
  };
  ['htmx:responseError', 'htmx:sendError', 'htmx:timeout'].forEach((name) => {
    document.addEventListener(name, showStale);
  });
  document.addEventListener('htmx:beforeRequest', (event) => {
    if (isRefresh(event) && document.hidden) event.preventDefault();
  });
})();
