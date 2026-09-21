/* =========================================================================
   zero_waste.js — goal CRUD, progress updates and status filtering.
   ========================================================================= */

(function () {
  "use strict";

  const Eco = window.Eco;
  let goals = [];
  let statusFilter = "";

  function renderSummary(summary) {
    Eco.countTo(Eco.$("#sumTotal"), summary.total, { decimals: 0 });
    Eco.countTo(Eco.$("#sumActive"), summary.active, { decimals: 0 });
    Eco.countTo(Eco.$("#sumDone"), summary.completed, { decimals: 0 });
    Eco.countTo(Eco.$("#sumProgress"), summary.avg_progress, { decimals: 0 });
  }

  function goalCard(goal) {
    const tone = goal.status === "Overdue" ? "coral" : goal.status === "Completed" ? "" : "amber";
    return (
      '<article class="goal-card">' +
      '<div class="goal-top"><h4>' + Eco.escape(goal.title) + "</h4>" +
      '<span class="chip chip-' + goal.status.toLowerCase() + '">' + Eco.escape(goal.status) + "</span></div>" +
      '<div class="goal-meta"><span>' + Eco.number(goal.current, 1) + " / " +
      Eco.number(goal.target, 1) + " " + Eco.escape(goal.unit || "kg") + "</span>" +
      "<span>" + goal.percent + "%</span></div>" +
      '<div class="bar thick ' + tone + '"><span data-fill="' + goal.percent + '"></span></div>' +
      '<div class="small muted" style="margin-top:8px"><i class="fa-regular fa-calendar"></i> ' +
      (goal.deadline ? "Due " + Eco.date(goal.deadline) : "No deadline") + "</div>" +
      '<div class="goal-actions">' +
      '<button class="btn btn-sm btn-secondary" data-progress="' + goal.id + '">Update progress</button>' +
      '<button class="btn btn-sm btn-ghost" data-edit="' + goal.id + '">Edit</button>' +
      '<button class="btn btn-sm btn-ghost" data-delete="' + goal.id + '" aria-label="Delete goal">' +
      '<i class="fa-solid fa-trash"></i></button></div></article>'
    );
  }

  function render() {
    const area = Eco.$("#goalsArea");
    const filtered = statusFilter ? goals.filter((g) => g.status === statusFilter) : goals;

    if (!goals.length) {
      area.innerHTML = Eco.emptyState({
        icon: "bullseye",
        title: "No zero-waste goals yet",
        message: "Pick one measurable change — less plastic, more compost — and give it a deadline.",
        action: { id: "createGoal", label: "Create your first goal" },
      });
      const btn = area.querySelector('[data-empty-action="createGoal"]');
      if (btn) btn.addEventListener("click", openCreate);
      return;
    }
    if (!filtered.length) {
      area.innerHTML = Eco.emptyState({
        icon: "filter-circle-xmark",
        title: "No " + statusFilter.toLowerCase() + " goals",
        message: "Switch the filter to see the rest of your plan.",
      });
      return;
    }

    area.innerHTML = '<div class="grid grid-2">' + filtered.map(goalCard).join("") + "</div>";
    Eco.$$("[data-fill]", area).forEach((s) => Eco.setBar(s, s.getAttribute("data-fill")));

    Eco.$$("[data-progress]", area).forEach(function (btn) {
      btn.addEventListener("click", () => openProgress(Number(btn.getAttribute("data-progress"))));
    });
    Eco.$$("[data-edit]", area).forEach(function (btn) {
      btn.addEventListener("click", () => openEdit(Number(btn.getAttribute("data-edit"))));
    });
    Eco.$$("[data-delete]", area).forEach(function (btn) {
      btn.addEventListener("click", () => removeGoal(Number(btn.getAttribute("data-delete"))));
    });
  }

  /* ------------------------------------------------------------- modals */
  function openCreate() {
    Eco.$("#goalModalTitle").textContent = "Create a goal";
    Eco.$("#goalForm").reset();
    Eco.$("#goalId").value = "";
    Eco.openModal("goalModal");
  }

  function openEdit(id) {
    const goal = goals.find((g) => g.id === id);
    if (!goal) return;
    Eco.$("#goalModalTitle").textContent = "Edit goal";
    Eco.$("#goalId").value = goal.id;
    Eco.$("#goalTitle").value = goal.title;
    Eco.$("#goalTarget").value = goal.target;
    Eco.$("#goalCurrent").value = goal.current;
    Eco.$("#goalUnit").value = goal.unit || "kg";
    Eco.$("#goalDeadline").value = goal.deadline || "";
    Eco.openModal("goalModal");
  }

  function openProgress(id) {
    const goal = goals.find((g) => g.id === id);
    if (!goal) return;
    Eco.$("#progressGoalId").value = goal.id;
    Eco.$("#progressGoalName").textContent =
      goal.title + " — target " + Eco.number(goal.target, 1) + " " + (goal.unit || "kg");
    Eco.$("#progressValue").value = goal.current;
    Eco.openModal("progressModal");
  }

  Eco.$("#createGoalBtn").addEventListener("click", openCreate);

  Eco.$("#goalForm").addEventListener("submit", async function (e) {
    e.preventDefault();
    Eco.$("#titleError").textContent = "";
    Eco.$("#targetError").textContent = "";

    const id = Eco.$("#goalId").value;
    const title = Eco.$("#goalTitle").value.trim();
    const target = parseFloat(Eco.$("#goalTarget").value);

    if (!title) { Eco.$("#titleError").textContent = "Give the goal a name."; return; }
    if (!target || target <= 0) { Eco.$("#targetError").textContent = "Enter a target above zero."; return; }

    const body = {
      title: title,
      target: target,
      current: parseFloat(Eco.$("#goalCurrent").value) || 0,
      unit: Eco.$("#goalUnit").value,
      deadline: Eco.$("#goalDeadline").value,
    };

    const res = id
      ? await Eco.api("/api/goals/" + id, { method: "PUT", body: body })
      : await Eco.api("/api/goals", { method: "POST", body: body });

    if (!res.success) { Eco.toast(res.error, "error", "Could not save goal"); return; }
    Eco.toast(res.message, "success", id ? "Goal updated" : "Goal created");
    Eco.closeModal("goalModal");
    load();
  });

  Eco.$("#progressForm").addEventListener("submit", async function (e) {
    e.preventDefault();
    const id = Eco.$("#progressGoalId").value;
    const value = parseFloat(Eco.$("#progressValue").value);
    if (isNaN(value) || value < 0) {
      Eco.toast("Enter a valid progress value.", "error", "Invalid value");
      return;
    }

    const res = await Eco.api("/api/goals/" + id, { method: "PUT", body: { current: value } });
    if (!res.success) { Eco.toast(res.error, "error", "Could not save"); return; }

    Eco.closeModal("progressModal");
    if (res.status === "Completed") {
      Eco.toast("Goal completed 🎉" + (res.points_awarded ? " +" + res.points_awarded + " eco points." : ""),
        "success", "Well done");
    } else {
      Eco.toast(res.message, "success", "Progress saved");
    }
    load();
  });

  async function removeGoal(id) {
    const ok = await Eco.confirm({
      title: "Delete this goal?",
      message: "Progress on this goal will be lost.",
      confirmText: "Delete",
      danger: true,
    });
    if (!ok) return;
    const res = await Eco.api("/api/goals/" + id, { method: "DELETE" });
    if (!res.success) { Eco.toast(res.error, "error", "Could not delete"); return; }
    Eco.toast(res.message, "success", "Deleted");
    load();
  }

  Eco.$$(".filter-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      statusFilter = btn.getAttribute("data-status");
      Eco.$$(".filter-btn").forEach((b) => (b.className = "btn btn-sm btn-ghost filter-btn"));
      btn.className = "btn btn-sm btn-secondary filter-btn";
      render();
    });
  });

  async function load() {
    const res = await Eco.api("/api/goals");
    if (!res.success) { Eco.toast(res.error, "error", "Could not load goals"); return; }
    goals = res.goals;
    renderSummary(res.summary);
    render();
  }

  document.addEventListener("DOMContentLoaded", load);
})();
