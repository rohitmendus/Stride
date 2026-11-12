(() => {
  if (window.strideBoardEvents || !window.Sortable || !window.htmx) return;
  window.strideBoardEvents = true;
  const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let pendingMove = null;

  const updateControls = () => {
    const board = document.getElementById("project-board");
    if (!board) return;
    const disabled = Boolean(pendingMove || board.dataset.moveFailed);
    board.querySelectorAll(".workspace-column-cards").forEach((list) => {
      Sortable.get(list)?.option("disabled", disabled);
    });
    board.querySelectorAll("[data-move-task]").forEach((handle) => {
      handle.setAttribute("aria-disabled", String(disabled));
    });
  };

  const moveTask = async (handle, status, beforeId = "") => {
    const board = handle.closest("#project-board");
    if (!board?.isConnected || pendingMove || board.dataset.moveFailed) return;
    pendingMove = handle;
    board.classList.add("is-saving");
    board.setAttribute("aria-busy", "true");
    updateControls();
    document.getElementById("task-live-status").textContent = "Saving task position…";
    try {
      await htmx.ajax("POST", handle.dataset.moveUrl, {
        source: handle, target: board, swap: "outerHTML", push: false,
        values: {status, before_id: beforeId},
      });
    } catch {
      // HTMX error events display the refresh notice; never retry an uncertain write.
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
    board.querySelectorAll("[data-move-task], #board-move-help").forEach((el) => { el.hidden = false; });
    board.querySelectorAll(".workspace-column-cards").forEach((list) => {
      if (Sortable.get(list)) return;
      let origin;
      Sortable.create(list, {
        group: "stride-tasks", draggable: ".workspace-task", handle: ".task-drag-handle",
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
          // Restore the last confirmed layout while the server saves the intended move.
          origin.parent.insertBefore(event.item, origin.next);
          origin = null;
          if (changed) moveTask(event.item.querySelector("[data-move-task]"), status, beforeId);
        },
      });
    });
    updateControls();
  };

  const failedMove = (event) => {
    const handle = event.detail.elt;
    if (!handle?.matches("[data-move-task]")) return;
    const board = handle.closest("#project-board");
    if (board) board.dataset.moveFailed = "true";
    const notice = document.getElementById("workspace-request-error");
    if (notice) notice.hidden = false;
    document.getElementById("task-live-status").textContent = "Move not confirmed. Refresh the board before trying again.";
    handle.focus();
    updateControls();
  };
  ["htmx:responseError", "htmx:sendError", "htmx:timeout"].forEach((name) => document.addEventListener(name, failedMove));

  document.addEventListener("keydown", (event) => {
    const handle = event.target.closest("[data-move-task]");
    if (!handle || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    if (!["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(event.key)) return;
    event.preventDefault();
    const card = handle.closest(".workspace-task");
    const column = card.closest("[data-task-status]");
    const cards = Array.from(column.querySelectorAll(".workspace-task"));
    const index = cards.indexOf(card);
    if (event.key === "ArrowUp" && index > 0) {
      moveTask(handle, column.dataset.taskStatus, cards[index - 1].dataset.taskId);
    } else if (event.key === "ArrowDown" && index < cards.length - 1) {
      moveTask(handle, column.dataset.taskStatus, cards[index + 2]?.dataset.taskId || "");
    } else if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      const destination = event.key === "ArrowLeft" ? column.previousElementSibling : column.nextElementSibling;
      if (destination?.matches("[data-task-status]")) moveTask(handle, destination.dataset.taskStatus);
    }
  });
  document.addEventListener("click", (event) => {
    if (pendingMove && event.target.closest("#project-board a")) {
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  }, true);
  document.addEventListener("taskMoved", (event) => {
    initBoard();
    document.querySelector(`[data-move-task="${Number(event.detail.task_id)}"]`)?.focus();
    document.getElementById("task-live-status").textContent = event.detail.message;
  });
  document.addEventListener("htmx:afterSettle", initBoard);
  document.addEventListener("htmx:beforeSwap", (event) => {
    if (pendingMove && event.detail.target === document.body) htmx.trigger(pendingMove, "htmx:abort");
  });
  document.addEventListener("htmx:beforeCleanupElement", (event) => {
    if (event.detail.elt.matches?.(".workspace-column-cards")) Sortable.get(event.detail.elt)?.destroy();
  });
  motion.addEventListener("change", () => {
    document.querySelectorAll(".workspace-column-cards").forEach((list) => {
      Sortable.get(list)?.option("animation", motion.matches ? 0 : 160);
    });
  });
  initBoard();
})();
