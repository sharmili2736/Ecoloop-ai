/* =========================================================================
   dashboard.js — fetches /api/dashboard once and renders every panel.
   ========================================================================= */

(function () {
  "use strict";

  const Eco = window.Eco;

  function deltaMarkup(el, value, invert, suffix) {
    if (!el) return;
    const n = Number(value) || 0;
    const improving = invert ? n > 0 : n < 0;
    const flat = Math.abs(n) < 0.5;
    el.className = "stat-delta " + (flat ? "flat" : improving ? "down" : "up");
    const icon = flat ? "minus" : n > 0 ? "arrow-trend-up" : "arrow-trend-down";
    el.innerHTML =
      '<i class="fa-solid fa-' + icon + '"></i> ' +
      (flat ? "No change" : Math.abs(n).toFixed(1) + "% " + (n > 0 ? "higher" : "lower")) +
      " " + (suffix || "vs last month");
  }

  function renderPillars(pillars) {
    const box = Eco.$("#pillarList");
    box.innerHTML = Object.keys(pillars).map(function (name) {
      return (
        '<div class="pillar">' +
        '<div class="pillar-top"><span>' + Eco.escape(name) + "</span><span>" +
        pillars[name] + "</span></div>" +
        '<div class="bar"><span data-fill="' + pillars[name] + '"></span></div></div>'
      );
    }).join("");
    Eco.$$("[data-fill]", box).forEach(function (span) {
      Eco.setBar(span, span.getAttribute("data-fill"));
    });
  }

  function recMarkup(rec) {
    return (
      '<div class="rec-item">' +
      '<div class="rec-icon"><i class="fa-solid fa-' + Eco.escape(rec.icon || "lightbulb") + '"></i></div>' +
      '<div class="rec-body">' +
      "<h4>" + Eco.escape(rec.title) + "</h4>" +
      "<p>" + Eco.escape(rec.description) + "</p>" +
      '<p style="color:var(--ink-700)"><strong>Do this:</strong> ' + Eco.escape(rec.action) + "</p>" +
      '<div class="rec-meta">' +
      '<span class="chip chip-' + Eco.escape((rec.priority || "low").toLowerCase()) + '">' +
      Eco.escape(rec.priority) + " priority</span>" +
      '<span class="chip"><i class="fa-solid fa-gauge"></i> ' + Eco.escape(rec.difficulty) + "</span>" +
      '<span class="chip"><i class="fa-solid fa-leaf"></i> ' + Eco.escape(rec.impact) + "</span>" +
      "</div></div></div>"
    );
  }

  function renderGoals(goals) {
    const box = Eco.$("#goalList");
    if (!goals.length) {
      box.innerHTML = Eco.emptyState({
        icon: "bullseye",
        title: "No goals yet",
        message: "Set a target like “cut plastic by 20%” and track it week by week.",
      }) + '<div style="text-align:center"><a class="btn btn-primary btn-sm" href="/zero-waste">Create a goal</a></div>';
      return;
    }
    box.innerHTML = goals.map(function (goal) {
      const percent = goal.target > 0 ? Math.min((goal.current / goal.target) * 100, 100) : 0;
      const tone = goal.status === "Overdue" ? "coral" : goal.status === "Completed" ? "" : "amber";
      return (
        '<div style="margin-bottom:15px">' +
        '<div class="pillar-top"><span>' + Eco.escape(goal.title) + "</span>" +
        '<span class="chip chip-' + goal.status.toLowerCase() + '">' + Eco.escape(goal.status) + "</span></div>" +
        '<div class="bar ' + tone + '"><span data-fill="' + percent + '"></span></div>' +
        '<div class="small muted" style="margin-top:5px">' +
        Eco.number(goal.current, 1) + " / " + Eco.number(goal.target, 1) + " " +
        Eco.escape(goal.unit || "kg") + " · " + percent.toFixed(0) + "%</div></div>"
      );
    }).join("");
    Eco.$$("[data-fill]", box).forEach((s) => Eco.setBar(s, s.getAttribute("data-fill")));
  }

  function renderChallenges(list) {
    const box = Eco.$("#challengeList");
    if (!list.length) {
      box.innerHTML = Eco.emptyState({
        icon: "trophy",
        title: "No challenges joined",
        message: "Challenges turn one-off effort into a habit, and each one is worth points.",
      }) + '<div style="text-align:center"><a class="btn btn-primary btn-sm" href="/challenges">Browse challenges</a></div>';
      return;
    }
    box.innerHTML = list.map(function (c) {
      return (
        '<div class="list-row">' +
        '<div class="rec-icon"><i class="fa-solid fa-' + Eco.escape(c.icon || "leaf") + '"></i></div>' +
        '<div class="grow"><h4>' + Eco.escape(c.title) + "</h4>" +
        '<div class="bar" style="margin-top:7px"><span data-fill="' + (c.progress || 0) + '"></span></div>' +
        '<p style="margin-top:5px">' + (c.progress || 0) + "% · " + c.points + " points</p></div>" +
        '<span class="chip chip-' + Eco.escape((c.status || "active").toLowerCase()) + '">' +
        Eco.escape(c.status) + "</span></div>"
      );
    }).join("");
    Eco.$$("[data-fill]", box).forEach((s) => Eco.setBar(s, s.getAttribute("data-fill")));
  }

  function renderBiodiversity(bio) {
    const box = Eco.$("#bioSummary");
    if (!bio.total) {
      box.innerHTML = Eco.emptyState({
        icon: "dove",
        title: "No observations yet",
        message: "Record the birds, trees and insects near you to build a local baseline.",
      }) + '<div style="text-align:center"><a class="btn btn-primary btn-sm" href="/biodiversity">Add an observation</a></div>';
      return;
    }
    const rows = bio.by_category.map(function (item) {
      const icons = { Bird: "dove", Plant: "seedling", Butterfly: "bug", Insect: "bug",
                      Tree: "tree", "Small Animal": "paw" };
      return (
        '<div class="list-row"><div class="rec-icon"><i class="fa-solid fa-' +
        (icons[item.category] || "leaf") + '"></i></div>' +
        '<div class="grow"><h4>' + Eco.escape(item.category) + "</h4>" +
        "<p>" + item.c + " observation" + (item.c === 1 ? "" : "s") + "</p></div></div>"
      );
    }).join("");

    box.innerHTML =
      '<div class="kv" style="margin-bottom:12px">' +
      '<div><div class="k">Observations</div><div class="v">' + bio.total + "</div></div>" +
      '<div><div class="k">This month</div><div class="v">' + bio.this_month + "</div></div></div>" + rows;
  }

  function renderCharts(data) {
    const charts = data.charts;
    const P = Eco.chartPalette;

    if (charts.waste_generated.some((v) => v > 0)) {
      Eco.barChart("wasteChart", charts.labels,
        [{ label: "Waste generated (kg)", data: charts.waste_generated, color: P.leaf }]);
    } else {
      Eco.chartEmpty("wasteChart", "Log waste records to see your monthly trend.");
    }

    if (charts.recycled.some((v) => v > 0)) {
      Eco.lineChart("rateChart", charts.labels,
        [{ label: "Recycling rate (%)", data: charts.recycling_rate, color: P.sky }],
        { scales: { y: { beginAtZero: true, suggestedMax: 100 } } });
    } else {
      Eco.chartEmpty("rateChart", "Log a recycling handover to start this chart.");
    }

    if (charts.carbon.some((v) => v > 0)) {
      Eco.lineChart("carbonChart", charts.labels,
        [{ label: "kg CO₂e", data: charts.carbon, color: P.amber }]);
    } else {
      Eco.chartEmpty("carbonChart", "Run a carbon assessment to see your trend.");
    }

    if (data.waste_categories.length) {
      Eco.doughnutChart("categoryChart", data.waste_categories.map(function (c) {
        return { label: c.category, value: c.total };
      }));
    } else {
      Eco.chartEmpty("categoryChart", "No waste categories recorded yet.");
    }

    const materials = Object.keys(data.totals.recycled_by_material);
    if (materials.length) {
      Eco.barChart("materialChart",
        materials.map(Eco.titleCase),
        [{ label: "Recycled (kg)", data: materials.map((m) => data.totals.recycled_by_material[m]), color: P.leafDark }]);
    } else {
      Eco.chartEmpty("materialChart", "Nothing recycled yet.");
    }
  }

  async function load() {
    const res = await Eco.api("/api/dashboard");
    if (!res.success) {
      Eco.toast(res.error, "error", "Could not load dashboard");
      return;
    }
    const data = res.data;

    Eco.$("#greetingLine").textContent = data.greeting + ", " + data.user.name.split(" ")[0] + " 🌱";
    Eco.$("#ecoPointsTop").textContent = Number(data.user.eco_points).toLocaleString();

    Eco.countTo(Eco.$("#statWaste"), data.totals.total_waste, { decimals: 1 });
    Eco.countTo(Eco.$("#statRecycled"), data.totals.total_recycled, { decimals: 1 });
    Eco.countTo(Eco.$("#statPlastic"), data.totals.plastic_recycled, { decimals: 1 });
    Eco.countTo(Eco.$("#statCo2"), data.totals.co2_saved, { decimals: 1 });

    deltaMarkup(Eco.$("#deltaWaste"), data.trends.waste_change_pct, false);
    deltaMarkup(Eco.$("#deltaRecycled"), data.trends.recyclable_change_pct, true);

    Eco.countTo(Eco.$("#scoreValue"), data.score.score, { decimals: 0 });
    Eco.setRing(Eco.$("#scoreRing"), data.score.score, 70);
    renderPillars(data.score.pillars);

    Eco.$("#insightText").textContent = data.insight;

    Eco.$("#topRecs").innerHTML = data.recommendations.length
      ? data.recommendations.map(recMarkup).join("")
      : '<p class="muted">Nothing to flag right now. Keep logging.</p>';
    Eco.$("#recList").innerHTML = data.recommendations.map(recMarkup).join("");

    renderGoals(data.goals);
    renderChallenges(data.challenges);
    renderBiodiversity(data.biodiversity);
    renderCharts(data);

    // Full recommendation list (the dashboard payload only carries the top three).
    const all = await Eco.api("/api/recommendations");
    if (all.success) {
      Eco.$("#recList").innerHTML = all.recommendations.map(recMarkup).join("");
    }
  }

  document.addEventListener("DOMContentLoaded", load);
})();
