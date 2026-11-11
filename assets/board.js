"use strict";
const $ = (id) => document.getElementById(id);
const statuses = ["To Do", "In Progress", "Review", "Completed"];
const people = ["Unassigned", "Alex Lee", "Jamie Kim", "Morgan Shah"];
const priorities = ["Low", "Medium", "High", "Critical"];
const storageKey = "stride.board.prototype.v1";
const icons = {
  chevron: '<path d="m9 5 4 7-4 7"/>',
  projects:
    '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  check:
    '<rect x="4" y="4" width="16" height="16" rx="4"/><path d="m8 12 3 3 5-6"/>',
  reset: '<path d="M4 11a8 8 0 1 1 2 7M4 4v7h7"/>',
  calendar:
    '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 11h18"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5"/>',
  board:
    '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16m6-16v16"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  filter:
    '<path d="M4 6h16M7 12h10m-7 6h4"/><circle cx="8" cy="6" r="2" fill="white"/><circle cx="15" cy="12" r="2" fill="white"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
  move: '<path d="M12 3v18M3 12h18m-12-6 3-3 3 3m-6 12 3 3 3-3M6 9l-3 3 3 3m12-6 3 3-3 3"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
};
function icon(name) {
  return `<span class="icon" aria-hidden="true"><svg viewBox="0 0 24 24">${icons[name] || ""}</svg></span>`;
}
document.querySelectorAll("[data-icon]").forEach((el) => {
  el.setAttribute("aria-hidden", "true");
  el.innerHTML = `<svg viewBox="0 0 24 24">${icons[el.dataset.icon] || ""}</svg>`;
});
const seed = [
  {
    id: 1,
    title: "Map out the onboarding flow",
    description:
      "Make the first five minutes feel effortless. Sketch the journey from sign-up to first project.",
    assignee: "Jamie Kim",
    priority: "High",
    deadline: "2026-11-16",
    status: "To Do",
  },
  {
    id: 2,
    title: "Write empty-state copy",
    description: "A little guidance for boards that are just getting started.",
    assignee: "Morgan Shah",
    priority: "Low",
    deadline: "2026-11-18",
    status: "To Do",
  },
  {
    id: 3,
    title: "Define notification preferences",
    description: "Decide what deserves a nudge—and what doesn’t.",
    assignee: "Alex Lee",
    priority: "Medium",
    deadline: "2026-11-20",
    status: "To Do",
  },
  {
    id: 4,
    title: "Build the Kanban board",
    description:
      "Four columns, clear priorities, and one place to keep work moving.",
    assignee: "Alex Lee",
    priority: "High",
    deadline: "2026-11-14",
    status: "In Progress",
  },
  {
    id: 5,
    title: "Design task detail panel",
    description: "All the context you need, without losing sight of the board.",
    assignee: "Jamie Kim",
    priority: "Medium",
    deadline: "2026-11-17",
    status: "In Progress",
  },
  {
    id: 6,
    title: "Connect project permissions",
    description: "Keep each team’s work visible to the right people.",
    assignee: "Alex Lee",
    priority: "Critical",
    deadline: "2026-11-09",
    status: "In Progress",
  },
  {
    id: 7,
    title: "Review mobile navigation",
    description: "A smaller screen should never mean a smaller experience.",
    assignee: "Jamie Kim",
    priority: "Medium",
    deadline: "2026-11-15",
    status: "Review",
  },
  {
    id: 8,
    title: "Check form validation states",
    description:
      "Helpful messages for missing details and things that go wrong.",
    assignee: "Morgan Shah",
    priority: "High",
    deadline: "2026-11-16",
    status: "Review",
  },
  {
    id: 9,
    title: "Set the visual direction",
    description: "A calm palette, considered typography, and room to breathe.",
    assignee: "Jamie Kim",
    priority: "Medium",
    deadline: "2026-11-06",
    status: "Completed",
  },
  {
    id: 10,
    title: "Create the project structure",
    description: "Lay the groundwork for Django, templates, and PostgreSQL.",
    assignee: "Alex Lee",
    priority: "High",
    deadline: "2026-11-07",
    status: "Completed",
  },
  {
    id: 11,
    title: "Outline the first release",
    description: "Keep it focused. Get the essentials right first.",
    assignee: "Morgan Shah",
    priority: "Low",
    deadline: "2026-11-05",
    status: "Completed",
  },
];
function validTask(t) {
  return (
    t &&
    Number.isSafeInteger(t.id) &&
    t.id > 0 &&
    typeof t.title === "string" &&
    t.title.trim().length > 0 &&
    t.title.length <= 160 &&
    typeof t.description === "string" &&
    t.description.length <= 3000 &&
    statuses.includes(t.status) &&
    priorities.includes(t.priority) &&
    people.includes(t.assignee) &&
    /^\d{4}-\d{2}-\d{2}$/.test(t.deadline) &&
    !Number.isNaN(new Date(`${t.deadline}T12:00:00`).getTime())
  );
}
let tasks = structuredClone(seed);
let storageWarning = false;
try {
  const saved = localStorage.getItem(storageKey);
  if (saved !== null) {
    const parsed = JSON.parse(saved);
    if (
      !Array.isArray(parsed) ||
      parsed.length > 1000 ||
      !parsed.every(validTask) ||
      new Set(parsed.map((t) => t.id)).size !== parsed.length
    )
      throw new Error("Invalid demo data");
    tasks = parsed;
  }
} catch {
  storageWarning = true;
}
let currentView = "board";
let myTasks = false;
let draggedId = null;
let toastTimer;
const esc = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
function avatar(name) {
  const person = {
    "Alex Lee": ["AL", "green"],
    "Jamie Kim": ["JK", "peach"],
    "Morgan Shah": ["MS", "blue"],
    Unassigned: ["—", "gray"],
  }[name];
  return `<span class="avatar avatar-${person[1]}" title="${esc(name)}" aria-label="${esc(name)}">${person[0]}</span>`;
}
function priorityTag(priority) {
  return `<span class="priority priority-${priority.toLowerCase()}">${priority}</span>`;
}
function dueDate(date) {
  return new Date(`${date}T12:00:00`).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}
function overdue(t) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return t.status !== "Completed" && new Date(`${t.deadline}T00:00:00`) < today;
}
function visibleTasks() {
  const query = $("search").value.toLowerCase().trim();
  return tasks.filter(
    (t) =>
      (!query ||
        `${t.title} ${t.description} STR-${String(t.id).padStart(3, "0")}`
          .toLowerCase()
          .includes(query)) &&
      (!$("priority-filter").value ||
        t.priority === $("priority-filter").value) &&
      (!$("assignee-filter").value ||
        t.assignee === $("assignee-filter").value) &&
      (!myTasks || t.assignee === "Alex Lee"),
  );
}
function render() {
  const visible = visibleTasks();
  $("task-total").textContent =
    `${visible.length === tasks.length ? tasks.length : `${visible.length} of ${tasks.length}`} tasks`;
  $("my-count").textContent = tasks.filter(
    (t) => t.assignee === "Alex Lee",
  ).length;
  $("filter-indicator").hidden = !(
    $("priority-filter").value || $("assignee-filter").value
  );
  $("board").innerHTML = statuses
    .map((status) => {
      const group = visible.filter((t) => t.status === status);
      return `<section class="column" data-status="${status}" aria-label="${status}"><div class="column-heading"><span class="status-dot" aria-hidden="true"></span><h2>${status}</h2><span class="column-count">${group.length}</span><button class="icon-button" data-add="${status}" aria-label="Add task to ${status}">${icon("plus")}</button></div><div class="column-cards">${group.map((t) => `<article class="task-card ${status === "Completed" ? "completed-card" : ""}" tabindex="0" role="button" draggable="true" data-id="${t.id}" aria-label="${esc(t.title)}, ${t.priority} priority, ${status}. Open to edit."><div class="card-top"><span class="task-id">STR-${String(t.id).padStart(3, "0")}</span>${priorityTag(t.priority)}</div><h3>${esc(t.title)}</h3><p class="card-description">${esc(t.description)}</p><div class="card-footer"><span class="due-date ${overdue(t) ? "overdue" : ""}" title="${esc(t.deadline)}${overdue(t) ? " · Overdue" : ""}">${icon(status === "Completed" ? "check" : "calendar")}${dueDate(t.deadline)}${overdue(t) ? " · Overdue" : ""}</span>${avatar(t.assignee)}</div></article>`).join("") || '<div class="empty-column">No tasks here. A little breathing room.</div>'}</div><button class="add-card" data-add="${status}">${icon("plus")}Add task</button></section>`;
    })
    .join("");
  $("list-view").innerHTML =
    visible
      .map(
        (t) =>
          `<button class="list-row" data-id="${t.id}"><span class="list-title">${esc(t.title)}<small>STR-${String(t.id).padStart(3, "0")} · ${esc(t.assignee)}</small></span><span class="list-status">${t.status}</span>${priorityTag(t.priority)}<span class="list-date">${dueDate(t.deadline)}</span></button>`,
      )
      .join("") ||
    '<p class="list-empty">No matching tasks. Try a different search or filter.</p>';
  $("board").hidden = currentView !== "board";
  $("list-view").hidden = currentView !== "list";
}
function toast(message) {
  clearTimeout(toastTimer);
  $("toast").textContent = message;
  $("toast").hidden = false;
  toastTimer = setTimeout(() => {
    $("toast").hidden = true;
  }, 3500);
}
function save(next) {
  try {
    localStorage.setItem(storageKey, JSON.stringify(next));
  } catch {
    toast("Could not save. Check browser storage and try again.");
    return false;
  }
  tasks = next;
  $("save-status").textContent =
    "Demo data · all changes saved in this browser";
  render();
  return true;
}
function openTask(id = null, status = "To Do") {
  const t = id ? tasks.find((t) => t.id === id) : null;
  if (id && !t) return;
  $("task-form").reset();
  $("task-id").value = t?.id || "";
  $("dialog-title").textContent = t ? "Task details" : "New task";
  $("task-title").value = t?.title || "";
  $("task-description").value = t?.description || "";
  $("task-status").value = t?.status || status;
  $("task-priority").value = t?.priority || "Medium";
  $("task-assignee").value = t?.assignee || "Unassigned";
  $("task-deadline").value = t?.deadline || "";
  $("delete-task").hidden = !t;
  $("delete-task").textContent = "Delete task";
  $("delete-task").dataset.confirm = "";
  $("form-error").hidden = true;
  $("task-dialog").showModal();
  $("task-title").focus();
}
function closeDialog() {
  $("task-dialog").close();
}
$("new-task").addEventListener("click", () => openTask());
$("close-dialog").addEventListener("click", closeDialog);
$("cancel-dialog").addEventListener("click", closeDialog);
$("task-dialog").addEventListener("click", (e) => {
  if (e.target === $("task-dialog")) {
    const rect = e.target.getBoundingClientRect();
    if (
      e.clientX < rect.left ||
      e.clientX > rect.right ||
      e.clientY < rect.top ||
      e.clientY > rect.bottom
    )
      closeDialog();
  }
});
$("task-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const id =
    Number($("task-id").value) || Math.max(0, ...tasks.map((t) => t.id)) + 1;
  const task = {
    id,
    title: $("task-title").value.trim(),
    description: $("task-description").value.trim(),
    status: $("task-status").value,
    priority: $("task-priority").value,
    assignee: $("task-assignee").value,
    deadline: $("task-deadline").value,
  };
  if (!validTask(task)) {
    $("form-error").textContent = "Add a title and a valid deadline.";
    $("form-error").hidden = false;
    return;
  }
  const exists = tasks.some((t) => t.id === id);
  const next = exists
    ? tasks.map((t) => (t.id === id ? task : t))
    : [...tasks, task];
  if (save(next)) {
    closeDialog();
    toast(exists ? "Task updated" : "Task added to the board");
  }
});
$("delete-task").addEventListener("click", () => {
  if (!$("delete-task").dataset.confirm) {
    $("delete-task").dataset.confirm = "yes";
    $("delete-task").textContent = "Confirm delete?";
    return;
  }
  if (save(tasks.filter((t) => t.id !== Number($("task-id").value)))) {
    closeDialog();
    toast("Task deleted");
  }
});
for (const el of [$("board"), $("list-view")]) {
  el.addEventListener("click", (e) => {
    const add = e.target.closest("[data-add]");
    const card = e.target.closest("[data-id]");
    if (add) openTask(null, add.dataset.add);
    else if (card) openTask(Number(card.dataset.id));
  });
}
$("board").addEventListener("keydown", (e) => {
  if ((e.key === "Enter" || e.key === " ") && e.target.matches(".task-card")) {
    e.preventDefault();
    openTask(Number(e.target.dataset.id));
  }
});
$("board").addEventListener("dragstart", (e) => {
  const card = e.target.closest(".task-card");
  if (!card) return;
  draggedId = Number(card.dataset.id);
  e.dataTransfer.setData("text/plain", String(draggedId));
  e.dataTransfer.effectAllowed = "move";
  card.classList.add("dragging");
});
$("board").addEventListener("dragend", () => {
  draggedId = null;
  document
    .querySelectorAll(".dragging,.drag-over")
    .forEach((el) => el.classList.remove("dragging", "drag-over"));
});
$("board").addEventListener("dragover", (e) => {
  const column = e.target.closest(".column");
  if (!column || !draggedId) return;
  e.preventDefault();
  e.dataTransfer.dropEffect = "move";
  document
    .querySelectorAll(".drag-over")
    .forEach((el) => el.classList.remove("drag-over"));
  column.classList.add("drag-over");
});
$("board").addEventListener("dragleave", (e) => {
  const column = e.target.closest(".column");
  if (column && !column.contains(e.relatedTarget))
    column.classList.remove("drag-over");
});
$("board").addEventListener("drop", (e) => {
  const column = e.target.closest(".column");
  if (!column || !draggedId) return;
  e.preventDefault();
  const moving = tasks.find((t) => t.id === draggedId);
  if (!moving) return;
  const other = e.target.closest(".task-card");
  const next = tasks.filter((t) => t.id !== draggedId);
  const updated = { ...moving, status: column.dataset.status };
  const targetIndex = other
    ? next.findIndex((t) => t.id === Number(other.dataset.id))
    : -1;
  if (targetIndex >= 0) next.splice(targetIndex, 0, updated);
  else next.push(updated);
  if (save(next)) toast(`Moved to ${updated.status}`);
  draggedId = null;
});
$("search").addEventListener("input", render);
$("priority-filter").addEventListener("change", render);
$("assignee-filter").addEventListener("change", render);
$("filter-toggle").addEventListener("click", () => {
  $("filters").hidden = !$("filters").hidden;
  $("filter-toggle").setAttribute(
    "aria-expanded",
    String(!$("filters").hidden),
  );
});
$("clear-filters").addEventListener("click", () => {
  $("priority-filter").value = "";
  $("assignee-filter").value = "";
  render();
});
document.querySelectorAll("[data-view]").forEach((btn) =>
  btn.addEventListener("click", () => {
    currentView = btn.dataset.view;
    document.querySelectorAll("[data-view]").forEach((tab) => {
      tab.classList.toggle("selected", tab === btn);
      tab.setAttribute("aria-pressed", String(tab === btn));
    });
    render();
  }),
);
function setMyTasks(value) {
  myTasks = value;
  $("my-tasks").classList.toggle("active", value);
  $("all-tasks").classList.toggle("active", !value);
  $("my-tasks").setAttribute("aria-pressed", String(value));
  $("all-tasks").setAttribute("aria-pressed", String(!value));
  render();
  closeMenu();
}
$("my-tasks").addEventListener("click", () => setMyTasks(true));
$("all-tasks").addEventListener("click", () => setMyTasks(false));
$("project-link").addEventListener("click", () => {
  $("search").value = "";
  $("priority-filter").value = "";
  $("assignee-filter").value = "";
  setMyTasks(false);
});
$("reset-demo").addEventListener("click", () => {
  if ($("reset-demo").dataset.confirm !== "yes") {
    $("reset-demo").dataset.confirm = "yes";
    $("reset-demo").innerHTML = `${icon("reset")}Confirm reset?`;
    return;
  }
  if (save(structuredClone(seed))) {
    $("reset-demo").dataset.confirm = "";
    $("reset-demo").innerHTML = `${icon("reset")}Reset demo`;
    $("search").value = "";
    $("priority-filter").value = "";
    $("assignee-filter").value = "";
    setMyTasks(false);
    toast("Demo board restored");
  }
});
const mobileNavigation = window.matchMedia("(max-width: 760px)");
function closeMenu() {
  const wasOpen = $("sidebar").classList.contains("open");
  $("sidebar").classList.remove("open");
  $("sidebar").inert = mobileNavigation.matches;
  document.querySelector("main").inert = false;
  $("scrim").hidden = true;
  $("menu-toggle").setAttribute("aria-expanded", "false");
  if (wasOpen && mobileNavigation.matches) $("menu-toggle").focus();
}
$("sidebar").inert = mobileNavigation.matches;
mobileNavigation.addEventListener("change", closeMenu);
$("menu-toggle").addEventListener("click", () => {
  $("sidebar").inert = false;
  $("sidebar").classList.add("open");
  document.querySelector("main").inert = true;
  $("scrim").hidden = false;
  $("menu-toggle").setAttribute("aria-expanded", "true");
  $("all-tasks").focus();
});
$("sidebar").addEventListener("keydown", (e) => {
  if (e.key !== "Tab" || !mobileNavigation.matches) return;
  const focusable = [...$("sidebar").querySelectorAll("a,button")];
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault();
    last.focus();
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault();
    first.focus();
  }
});
$("scrim").addEventListener("click", closeMenu);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !$("task-dialog").open) {
    closeMenu();
    $("menu-toggle").focus();
  }
  if (
    e.key === "/" &&
    !$("task-dialog").open &&
    !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)
  ) {
    e.preventDefault();
    $("search").focus();
  }
});
window.addEventListener("storage", (e) => {
  if (e.key !== storageKey) return;
  try {
    const next = JSON.parse(e.newValue);
    if (
      Array.isArray(next) &&
      next.every(validTask) &&
      new Set(next.map((t) => t.id)).size === next.length
    ) {
      tasks = next;
      render();
      toast("Board updated from another tab");
    }
  } catch {
    /* Keep the last valid board. */
  }
});
render();
if (storageWarning) {
  $("save-status").textContent = "Demo data · previous local data unavailable";
  toast("Could not load saved data. Showing the example board.");
}
