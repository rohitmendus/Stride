(() => {
  if (window.strideNotificationEvents) return;
  window.strideNotificationEvents = true;
  let wasOpen = false;
  let focusKey = null;
  const root = () => document.getElementById('workspace-notifications');
  document.addEventListener('click', (event) => {
    const element = root();
    if (element && !element.contains(event.target)) element.querySelector('details')?.removeAttribute('open');
  });
  document.addEventListener('keydown', (event) => {
    const menu = root()?.querySelector('details[open]');
    if (event.key === 'Escape' && menu && !document.querySelector('dialog[open]')) {
      menu.open = false;
      menu.querySelector('summary').focus();
    }
  });
  document.addEventListener('htmx:beforeSwap', (event) => {
    const element = root();
    if (event.detail.target !== element) return;
    wasOpen = Boolean(element.querySelector('details')?.open);
    const active = document.activeElement;
    focusKey = element.contains(active)
      ? active.dataset.notificationId || active.dataset.notificationAction || 'toggle' : null;
  });
  document.addEventListener('htmx:afterSwap', (event) => {
    if (event.detail.target !== root()) return;
    root().querySelector('details').open = wasOpen;
  });
  document.addEventListener('htmx:afterSettle', (event) => {
    if (event.detail.target !== root() || !focusKey) return;
    const target = root().querySelector(`[data-notification-id="${focusKey}"], [data-notification-action="${focusKey}"]`);
    (target && !target.disabled ? target : root().querySelector('summary')).focus({preventScroll: true});
    focusKey = null;
  });
})();
