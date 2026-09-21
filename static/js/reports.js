/* =========================================================================
   reports.js — builds the monthly report view from /api/reports/monthly.
   ========================================================================= */

(function () {
  "use strict";

  const Eco = window.Eco;

  function kv(items) {
    return '<div class="kv">' + items.map(function (item) {
      return '<div><div class="k">' + Eco.escape(item[0]) + '</div><div class="v">' +
        Eco.escape(item[1]) + "</div></div>";
    }).join("") + "</div>";
  }

  function render(report) {
    const w = report.waste, c = report.carbon, s = report.score;

    const pillars = Object.keys(s.pillars).map(function (name) {
      return (
        '<div class="pillar"><div class="pillar-top"><span>' + Eco.escape(name) +
        "</span><span>" + s.pillars[name] + " / 100</span></div>" +
        '<div class="bar"><span data-fill="' + s.pillars[name] + '"></span></div></div>'
      );
    }).join("");

    const goals = report.goals.length
      ? '<div class="table-wrap"><table class="data"><thead><tr><th>Goal</th><th>Progress</th>' +
        "<th>Status</th><th>Deadline</th></tr></thead><tbody>" +
        report.goals.map(function (g) {
          return "<tr><td>" + Eco.escape(g.title) + "</td><td>" +
            Eco.number(g.current, 1) + " / " + Eco.number(g.target, 1) + " " + Eco.escape(g.unit) +
            '</td><td><span class="chip chip-' + g.status.toLowerCase() + '">' + Eco.escape(g.status) +
            "</span></td><td>" + (g.deadline ? Eco.date(g.deadline) : "—") + "</td></tr>";
        }).join("") + "</tbody></table></div>"
      : '<p class="muted">No goals tracked in this period.</p>';

    const observations = report.biodiversity.records.length
      ? '<div class="table-wrap"><table class="data"><thead><tr><th>Species</th><th>Category</th>' +
        "<th>Location</th><th>Date</th></tr></thead><tbody>" +
        report.biodiversity.records.map(function (o) {
          return "<tr><td>" + Eco.escape(o.species) + "</td><td>" + Eco.escape(o.category) +
            "</td><td>" + Eco.escape(o.location || "—") + "</td><td>" +
            Eco.date(o.observation_date) + "</td></tr>";
        }).join("") + "</tbody></table></div>"
      : '<p class="muted">No observations recorded in this period.</p>';

    const completed = report.challenges.completed.length
      ? report.challenges.completed.map(function (ch) {
          return '<span class="chip chip-completed"><i class="fa-solid fa-check"></i> ' +
            Eco.escape(ch.title) + " · " + ch.points + " pts</span>";
        }).join(" ")
      : '<p class="muted">No challenges completed in this period.</p>';

    Eco.$("#reportArea").innerHTML =
      '<article class="card">' +
      '<div class="card-head"><div><h2 style="margin:0">Sustainability report — ' +
      Eco.escape(report.period.label) + "</h2>" +
      '<p class="muted small" style="margin:4px 0 0">' + Eco.escape(report.user.name) + " · " +
      Eco.escape(report.user.organization) + " · generated " + Eco.escape(report.generated_at) +
      "</p></div></div>" +

      '<div class="report-section"><h3>Waste and recycling</h3>' +
      kv([
        ["Total waste generated", Eco.number(w.generated, 1) + " kg"],
        ["Total recycled", Eco.number(w.recycled, 1) + " kg"],
        ["Plastic diverted", Eco.number(w.plastic_recycled, 1) + " kg"],
        ["Recycling rate", w.recycling_rate + "%"],
        ["Landfill avoided", Eco.number(w.landfill_avoided, 1) + " kg"],
      ]) + "</div>" +

      '<div class="report-section"><h3>Carbon footprint (estimated)</h3>' +
      kv([
        ["Monthly estimate", Eco.number(c.monthly_estimate, 1) + " kg CO₂e"],
        ["Electricity", Eco.number(c.electricity, 1) + " kg"],
        ["Transport", Eco.number(c.transport, 1) + " kg"],
        ["Food", Eco.number(c.food, 1) + " kg"],
        ["Waste", Eco.number(c.waste, 1) + " kg"],
        ["CO₂e avoided by recycling", Eco.number(c.co2_saved, 1) + " kg"],
      ]) +
      '<p class="small muted" style="margin-top:10px">' + Eco.escape(report.basis) + "</p></div>" +

      '<div class="report-section"><h3>Sustainability score: ' + s.score + " / 100</h3>" +
      pillars + "</div>" +

      '<div class="report-section"><h3>Eco points and challenges</h3>' +
      kv([
        ["Eco points", Eco.number(report.user.eco_points, 0)],
        ["Challenges joined", String(report.challenges.joined)],
        ["Challenges completed", String(report.challenges.completed.length)],
        ["Points from challenges", String(report.challenges.points_from_challenges)],
      ]) +
      '<div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">' + completed + "</div></div>" +

      '<div class="report-section"><h3>Zero-waste goals</h3>' + goals + "</div>" +

      '<div class="report-section"><h3>Biodiversity observations (' +
      report.biodiversity.count + ")</h3>" + observations + "</div>" +

      "</article>";

    Eco.$$("[data-fill]", Eco.$("#reportArea")).forEach((s2) => Eco.setBar(s2, s2.getAttribute("data-fill")));
  }

  async function generate() {
    const month = Eco.$("#monthSelect").value;
    const year = Eco.$("#yearSelect").value;
    const btn = Eco.$("#generateBtn");

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generating…';
    Eco.$("#reportArea").innerHTML = '<div class="card"><div class="skeleton skeleton-card"></div></div>';

    const res = await Eco.api("/api/reports/monthly?year=" + year + "&month=" + month);

    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-file-circle-plus"></i> Generate report';

    if (!res.success) { Eco.toast(res.error, "error", "Could not generate report"); return; }

    render(res.report);
    const query = "?year=" + year + "&month=" + month;
    Eco.$("#printLink").href = "/reports/print" + query;
    Eco.$("#downloadLink").href = "/reports/download" + query;
    Eco.$("#exportActions").hidden = false;
    Eco.toast("Report for " + res.report.period.label + " is ready.", "success", "Report generated");
  }

  Eco.$("#generateBtn").addEventListener("click", generate);
  document.addEventListener("DOMContentLoaded", generate);
})();
