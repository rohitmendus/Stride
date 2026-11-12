(() => {
  if (window.strideDashboardEvents) return;
  window.strideDashboardEvents = true;
  let board = null;
  let socket = null;
  let reconnectTimer, refreshTimer, heartbeatTimer;
  let attempts = 0;
  let dirty = false;
  let inFlight = false;
  let sessionEnded = false;
  const connectionStatus = () => {
    const label = board?.querySelector('[data-dashboard-connection]');
    if (label) label.textContent = socket && socket.readyState === window.WebSocket?.OPEN
      ? 'Live updates' : 'Connecting live updates…';
  };
  const flush = () => {
    if (!board?.isConnected || document.hidden || inFlight || !dirty) return;
    dirty = false;
    htmx.trigger(board, 'dashboardChanged');
  };
  const refresh = () => {
    dirty = true;
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(flush, 100);
  };
  const stop = () => {
    clearTimeout(reconnectTimer);
    clearTimeout(refreshTimer);
    clearTimeout(heartbeatTimer);
    const old = socket;
    socket = null;
    old?.close();
    board = null;
    inFlight = dirty = false;
  };
  const connect = () => {
    if (!board?.isConnected || socket || sessionEnded || !window.WebSocket) return;
    const url = new URL(board.dataset.dashboardSocket, location.href);
    url.protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(url);
    socket = ws;
    const heartbeat = () => {
      clearTimeout(heartbeatTimer);
      heartbeatTimer = setTimeout(() => ws.close(), 45000);
    };
    heartbeat();
    ws.onopen = () => {
      if (socket !== ws) return;
      attempts = 0;
      connectionStatus();
      heartbeat();
      refresh();
    };
    ws.onmessage = (event) => {
      if (socket !== ws) return;
      let message;
      try { message = JSON.parse(event.data); } catch { return; }
      heartbeat();
      if (message.type === 'ping') ws.send(JSON.stringify({type: 'pong'}));
      if (message.type === 'dashboard.changed') refresh();
    };
    ws.onclose = (event) => {
      if (socket !== ws) return;
      clearTimeout(heartbeatTimer);
      socket = null;
      connectionStatus();
      if (event.code === 4401) {
        sessionEnded = true;
        refresh();
        return;
      }
      reconnectTimer = setTimeout(connect, Math.min(1000 * 2 ** attempts++, 30000));
    };
  };
  const init = () => {
    const next = document.getElementById('dashboard-content');
    if (next !== board) {
      stop();
      board = next;
      sessionEnded = false;
      attempts = 0;
      connect();
    }
    connectionStatus();
  };
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
    if (!isRefresh(event)) return;
    if (document.hidden) { event.preventDefault(); dirty = true; return; }
    inFlight = true;
    dirty = false;
  });
  document.addEventListener('htmx:afterRequest', (event) => {
    if (event.detail.target !== board) return;
    inFlight = false;
    if (dirty) refresh();
  });
  document.addEventListener('htmx:afterSettle', init);
  document.addEventListener('htmx:beforeCleanupElement', (event) => {
    if (event.detail.elt === board) stop();
  });
  window.addEventListener('pagehide', stop);
  window.addEventListener('pageshow', init);
  init();
})();
