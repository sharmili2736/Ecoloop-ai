/* =========================================================================
   challenges.js — join challenges, update progress, render badges.
   ========================================================================= */

(function () {
  "use strict";

  const Eco = window.Eco;
  let challenges = [];

  function card(c) {
    const joined = c.joined;
    const done = c.status === "Completed";
    return (
      '<article class="card challenge-card">' +
      '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px">' +
      '<div class="c-icon"><i class="fa-solid fa-' + Eco.escape(c.icon || "leaf") + '"></i></div>' +
      '<span class="chip chip-' + (done ? "completed" : joined ? "active" : "low") + '">' +
      (done ? "Completed" : joined ? "In progress" : c.duration) + "</span></div>" +
      "<h3>" + Eco.escape(c.title) + "</h3>" +
      "<p>" + Eco.escape(c.description) + "</p>" +
      '<div class="challenge-meta">' +
      '<span class="chip"><i class="fa-regular fa-clock"></i> ' + Eco.escape(c.duration) + "</span>" +
      '<span class="chip"><i class="fa-solid fa-star"></i> ' + c.points + " points</span></div>" +
      (joined
        ? '<div><div class="bar"><span data-fill="' + c.progress + '"></span></div>' +
          '<div class="small muted" style="margin-top:6px">' + c.progress + "% complete</div></div>"
        : "") +
      '<div style="display:flex;gap:8px;flex-wrap:wrap">' +
      (done
        ? '<span class="btn btn-sm btn-secondary" aria-disabled="true">Challenge completed 🎉</span>'
        : joined
          ? '<button class="btn btn-sm btn-primary" data-progress="' + c.id + '">Update progress</button>' +
            '<button class="btn btn-sm btn-ghost" data-leave="' + c.id + '">Leave</button>'
          : '<button class="btn btn-sm btn-primary" data-join="' + c.id + '">Join challenge</button>') +
      "</div></article>"
    );
  }

  function renderBadges(badges) {
    Eco.$("#badgeGrid").innerHTML = badges.map(function (b) {
      return (
        '<div class="badge-card' + (b.earned ? " earned" : "") + '">' +
        '<div class="ring"><i class="fa-solid fa-' + Eco.escape(b.icon) + '"></i></div>' +
        "<h4>" + Eco.escape(b.name) + "</h4>" +
        "<p>" + Eco.escape(b.description) + "</p>" +
        (b.earned
          ? '<span class="chip chip-completed" style="margin-top:8px">Earned</span>'
          : '<div class="bar" style="margin-top:9px"><span data-fill="' + b.progress + '"></span></div>' +
            '<p class="small muted" style="margin-top:5px">' + b.progress + "%</p>") +
        "</div>"
      );
    }).join("");
    Eco.$$("[data-fill]", Eco.$("#badgeGrid")).forEach((s) => Eco.setBar(s, s.getAttribute("data-fill")));
  }

  function render() {
    const grid = Eco.$("#challengeGrid");
    grid.innerHTML = challenges.map(card).join("");
    Eco.$$("[data-fill]", grid).forEach((s) => Eco.setBar(s, s.getAttribute("data-fill")));

    Eco.$$("[data-join]", grid).forEach(function (btn) {
      btn.addEventListener("click", () => join(btn.getAttribute("data-join")));
    });
    Eco.$$("[data-progress]", grid).forEach(function (btn) {
      btn.addEventListener("click", () => openProgress(Number(btn.getAttribute("data-progress"))));
    });
    Eco.$$("[data-leave]", grid).forEach(function (btn) {
      btn.addEventListener("click", () => leave(btn.getAttribute("data-leave")));
    });
  }

  async function join(id) {
    const res = await Eco.api("/api/challenges/" + id + "/join", { method: "POST" });
    if (!res.success) { Eco.toast(res.error, "error", "Could not join"); return; }
    Eco.toast(res.message, "success", "Joined");
    load();
  }

  async function leave(id) {
    const ok = await Eco.confirm({
      title: "Leave this challenge?",
      message: "Your progress on it will be cleared.",
      confirmText: "Leave",
      danger: true,
    });
    if (!ok) return;
    const res = await Eco.api("/api/challenges/" + id + "/leave", { method: "DELETE" });
    if (!res.success) { Eco.toast(res.error, "error", "Could not leave"); return; }
    Eco.toast(res.message, "info", "Left challenge");
    load();
  }

  function openProgress(id) {
    const c = challenges.find((x) => x.id === id);
    if (!c) return;
    Eco.$("#progressChallengeId").value = id;
    Eco.$("#progressName").textContent = c.title + " · " + c.points + " points on completion";
    Eco.$("#progressRange").value = c.progress;
    Eco.$("#progressLabel").textContent = c.progress;
    Eco.openModal("progressModal");
  }

  Eco.$("#progressRange").addEventListener("input", function () {
    Eco.$("#progressLabel").textContent = this.value;
  });

  Eco.$("#progressForm").addEventListener("submit", async function (e) {
    e.preventDefault();
    const id = Eco.$("#progressChallengeId").value;
    const progress = Number(Eco.$("#progressRange").value);

    const res = await Eco.api("/api/challenges/" + id + "/progress", {
      method: "PUT", body: { progress: progress },
    });
    if (!res.success) { Eco.toast(res.error, "error", "Could not save"); return; }

    Eco.closeModal("progressModal");
    if (res.completed) {
      Eco.toast("Challenge completed 🎉 +" + res.points_awarded + " eco points.", "success", "Well done");
    } else {
      Eco.toast(res.message, "success", "Progress saved");
    }
    Eco.$("#ecoPointsTop").textContent = Number(res.eco_points).toLocaleString();
    Eco.$("#pointsPanel").textContent = Number(res.eco_points).toLocaleString();
    load();
  });

  async function load() {
    const res = await Eco.api("/api/challenges");
    if (!res.success) { Eco.toast(res.error, "error", "Could not load challenges"); return; }
    challenges = res.challenges;

    Eco.countTo(Eco.$("#sumJoined"), res.summary.joined, { decimals: 0 });
    Eco.countTo(Eco.$("#sumCompleted"), res.summary.completed, { decimals: 0 });
    Eco.countTo(Eco.$("#sumPoints"), res.summary.points_earned, { decimals: 0 });
    Eco.countTo(Eco.$("#sumBadges"), res.badges.filter((b) => b.earned).length, { decimals: 0 });

    render();
    renderBadges(res.badges);
  }

  document.addEventListener("DOMContentLoaded", load);
})();
