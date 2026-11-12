(() => {
  if (window.strideBoardEvents || !window.htmx) return;
  window.strideBoardEvents = true;
  const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let pendingMove = null;
  let projectId = null;
  let filtersOpen = false;
  let viewFocus = null;

  const updateControls = () => {
    const board = document.getElementById("project-board");
    if (!board) return;
    const disabled = Boolean(pendingMove || board.dataset.moveFailed);
    board.querySelectorAll(".workspace-column-cards").forEach((list) => {
      window.Sortable?.get(list)?.option("disabled", disabled);
    });
    board.querySelectorAll("[data-move-task]").forEach((card) => {
      card.dataset.moveDisabled = String(disabled);
    });
    board.querySelectorAll("#task-filters input, #task-filters select, #task-filters button").forEach((input) => {
      input.disabled = Boolean(pendingMove);
    });
  };

  const moveTask = async (card, status, beforeId = "") => {
    const board = card?.closest("#project-board");
    if (!board?.isConnected || pendingMove || board.dataset.moveFailed) return;
    pendingMove = card;
    board.classList.add("is-saving");
    board.setAttribute("aria-busy", "true");
    updateControls();
    document.getElementById("task-live-status").textContent = "Saving task position…";
    const saveStatus = document.getElementById("save-status");
    if (saveStatus) saveStatus.textContent = "Saving…";
    try {
      await htmx.ajax("POST", card.dataset.moveUrl, {
        source: card, target: board, swap: "outerHTML", push: false,
        values: {status, before_id: beforeId},
      });
    } catch {
      // Failed writes are reported by HTMX events and are never retried automatically.
    } finally {
      pendingMove = null;
      board.classList.remove("is-saving");
      board.removeAttribute("aria-busy");
      initBoard();
    }
  };

  const initBoard = () => {
    const board = document.getElementById("project-board");
    if (!board) return;
    const form = board.querySelector("#task-filters");
    const hasFilters = Boolean(form?.elements.priority?.value || form?.elements.assignee?.value);
    if (projectId !== board.dataset.projectId) {
      projectId = board.dataset.projectId;
      filtersOpen = hasFilters;
    }
    if (hasFilters) filtersOpen = true;
    const filters = board.querySelector("#filters");
    if (filters) filters.hidden = !filtersOpen;
    const toggle = board.querySelector("[data-filter-toggle]");
    if (toggle) {
      toggle.hidden = false;
      toggle.setAttribute("aria-expanded", String(filtersOpen));
    }
    document.querySelectorAll("[data-my-task-count]").forEach((count) => { count.textContent = board.dataset.myCount; });

    if (window.Sortable) board.querySelectorAll(".workspace-column-cards").forEach((list) => {
      if (Sortable.get(list)) return;
      let origin;
      Sortable.create(list, {
        group: "stride-tasks", draggable: ".workspace-task",
        filter: ".workspace-task:not([data-move-task])", preventOnFilter: false,
        animation: motion.matches ? 0 : 160, direction: "vertical",
        ghostClass: "task-drag-ghost", chosenClass: "task-drag-chosen",
        delay: 180, delayOnTouchOnly: true, touchStartThreshold: 4,
        fallbackTolerance: 4,
        onStart: (event) => { origin = {parent: event.from, next: event.item.nextSibling}; },
        onEnd: (event) => {
          if (!origin || !event.item.isConnected) return;
          const status = event.to.closest("[data-task-status]").dataset.taskStatus;
          const next = event.item.nextElementSibling;
          const beforeId = next?.matches(".workspace-task") ? next.dataset.taskId : "";
          const changed = event.from !== event.to || event.oldDraggableIndex !== event.newDraggableIndex;
          origin.parent.insertBefore(event.item, origin.next?.parentNode === origin.parent ? origin.next : null);
          origin = null;
          if (changed) moveTask(event.item, status, beforeId);
        },
      });
    });
    updateControls();
  };

  const failedMove = (event) => {
    const card = event.detail.elt;
    if (!card?.matches("[data-move-task]")) return;
    const board = card.closest("#project-board");
    if (board) board.dataset.moveFailed = "true";
    const notice = document.getElementById("workspace-request-error");
    if (notice) notice.hidden = false;
    window.strideNotify?.("Could not save. Refresh the board and try again.", undefined, false);
    card.focus();
    updateControls();
  };
  ["htmx:responseError", "htmx:sendError", "htmx:timeout"].forEach((name) => document.addEventListener(name, failedMove));

  document.addEventListener("keydown", (event) => {
    const card = event.target.closest(".workspace-task");
    if (card && event.key === " " && event.target === card && !event.altKey && !event.ctrlKey && !event.metaKey) {
      event.preventDefault();
      card.click();
    }
    if (event.key === "/" && !event.altKey && !event.ctrlKey && !event.metaKey &&
        !event.target.closest("input, textarea, select, [contenteditable='true']") &&
        !document.querySelector("dialog[open]")) {
      const search = document.getElementById("search");
      if (search) { event.preventDefault(); search.focus(); }
    }
    if (!card?.hasAttribute("data-move-task") || !event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    if (!["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(event.key)) return;
    event.preventDefault();
    const column = card.closest("[data-task-status]");
    if (!column) return;
    const cards = Array.from(column.querySelectorAll(".workspace-task"));
    const index = cards.indexOf(card);
    if (event.key === "ArrowUp" && index > 0) {
      moveTask(card, column.dataset.taskStatus, cards[index - 1].dataset.taskId);
    } else if (event.key === "ArrowDown" && index < cards.length - 1) {
      moveTask(card, column.dataset.taskStatus, cards[index + 2]?.dataset.taskId || "");
    } else if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      const destination = event.key === "ArrowLeft" ? column.previousElementSibling : column.nextElementSibling;
      if (destination?.matches("[data-task-status]")) moveTask(card, destination.dataset.taskStatus);
    }
  });
  document.addEventListener("click", (event) => {
    if (pendingMove && event.target.closest("#project-board a")) {
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  }, true);
  document.addEventListener("click", (event) => {
    const toggle = event.target.closest("[data-filter-toggle]");
    if (!toggle) return;
    filtersOpen = !filtersOpen;
    document.getElementById("filters").hidden = !filtersOpen;
    toggle.setAttribute("aria-expanded", String(filtersOpen));
  });
  document.addEventListener("htmx:beforeRequest", (event) => {
    viewFocus = event.detail.elt.dataset.view || null;
  });
  document.addEventListener("taskMoved", (event) => {
    initBoard();
    document.querySelector(`[data-task-id="${Number(event.detail.task_id)}"]`)?.focus();
  });
  document.addEventListener("taskSaved", initBoard);
  document.addEventListener("htmx:afterSettle", (event) => {
    initBoard();
    if (viewFocus && event.detail.target?.id === "project-board") {
      document.querySelector(`#project-board [data-view="${viewFocus}"]`)?.focus({preventScroll: true});
      viewFocus = null;
    }
  });
  document.addEventListener("htmx:beforeSwap", (event) => {
    if (pendingMove && event.detail.target === document.body) htmx.trigger(pendingMove, "htmx:abort");
  });
  document.addEventListener("htmx:beforeCleanupElement", (event) => {
    if (event.detail.elt.matches?.(".workspace-column-cards")) window.Sortable?.get(event.detail.elt)?.destroy();
  });
  motion.addEventListener("change", () => {
    document.querySelectorAll(".workspace-column-cards").forEach((list) => {
      window.Sortable?.get(list)?.option("animation", motion.matches ? 0 : 160);
    });
  });
  initBoard();
})();
