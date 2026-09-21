/* =========================================================================
   recycling.js — records, charts, material goals and filtering.
   ========================================================================= */

(function () {
  "use strict";

  const Eco = window.Eco;
  let records = [];

  function renderSummary(summary) {
    Eco.countTo(Eco.$("#sumTotal"), summary.total_recycled, { decimals: 1 });
    Eco.countTo(Eco.$("#sumPlastic"), summary.by_material.plastic || 0, { decimals: 1 });
    Eco.countTo(Eco.$("#sumPaper"), summary.by_material.paper || 0, { decimals: 1 });
    Eco.countTo(Eco.$("#sumCo2"), summary.co2_saved, { decimals: 1 });
    Eco.$("#recordCount").textContent = summary.records + " record" + (summary.records === 1 ? "" : "s");
  }

  function renderCharts(data) {
    const materials = Object.keys(data.summary.by_material);
    if (materials.length) {
      Eco.doughnutChart("materialChart", materials.map(function (m) {
        return { label: Eco.titleCase(m), value: data.summary.by_material[m] };
      }));
    } else {
      Eco.chartEmpty("materialChart", "Add a record to see your material split.");
    }

    if (data.trend.recycled.some((v) => v > 0)) {
      Eco.barChart("trendChart", data.trend.labels,
        [{ label: "Recycled (kg)", data: data.trend.recycled, color: Eco.chartPalette.leafDark }]);
    } else {
      Eco.chartEmpty("trendChart", "No recycling logged in the last six months.");
    }
  }

  function renderGoals(goals) {
    Eco.$("#goalsArea").innerHTML = goals.map(function (goal) {
      return (
        '<div class="pillar">' +
        '<div class="pillar-top"><span>' + Eco.escape(goal.material) + " recycling goal</span>" +
        "<span>" + Eco.number(goal.current, 1) + " / " + goal.target + " kg</span></div>" +
        '<div class="bar thick"><span data-fill="' + goal.percent + '"></span></div>' +
        '<div class="small muted" style="margin-top:5px">' + goal.percent + "% complete</div></div>"
      );
    }).join("");
    Eco.$$("[data-fill]", Eco.$("#goalsArea")).forEach((s) => Eco.setBar(s, s.getAttribute("data-fill")));
  }

  function renderRecords() {
    const area = Eco.$("#recordsArea");
    const material = Eco.$("#filterMaterial").value;
    const from = Eco.$("#filterFrom").value;
    const to = Eco.$("#filterTo").value;

    const filtered = records.filter(function (r) {
      if (material && r.material !== material) return false;
      const day = (r.created_at || "").slice(0, 10);
      if (from && day < from) return false;
      if (to && day > to) return false;
      return true;
    });

    if (!records.length) {
      area.innerHTML = Eco.emptyState({
        icon: "recycle",
        title: "No recycling records yet",
        message: "Start tracking your recycling journey today.",
        action: { id: "addRecycling", label: "Add recycling record" },
      });
      const btn = area.querySelector('[data-empty-action="addRecycling"]');
      if (btn) btn.addEventListener("click", () => Eco.openModal("recyclingModal"));
      return;
    }
    if (!filtered.length) {
      area.innerHTML = Eco.emptyState({
        icon: "filter-circle-xmark",
        title: "Nothing matches those filters",
        message: "Try another material or widen the date range.",
      });
      return;
    }

    area.innerHTML =
      '<div class="table-wrap"><table class="data"><thead><tr>' +
      "<th>Material</th><th>Quantity</th><th>Method</th><th>Date</th><th>Notes</th><th></th>" +
      "</tr></thead><tbody>" +
      filtered.map(function (r) {
        return (
          "<tr><td><strong>" + Eco.escape(r.material) + "</strong></td>" +
          "<td>" + Eco.number(r.quantity, 2) + " " + Eco.escape(r.unit) + "</td>" +
          '<td><span class="chip">' + Eco.escape(r.method || "—") + "</span></td>" +
          "<td>" + Eco.date(r.created_at) + "</td>" +
          '<td class="small muted">' + Eco.escape(r.notes || "—") + "</td>" +
          '<td class="text-right"><button class="icon-btn" data-delete="' + r.id +
          '" aria-label="Delete record"><i class="fa-solid fa-trash"></i></button></td></tr>'
        );
      }).join("") + "</tbody></table></div>";

    Eco.$$("[data-delete]", area).forEach(function (btn) {
      btn.addEventListener("click", () => remove(btn.getAttribute("data-delete")));
    });
  }

  async function remove(id) {
    const ok = await Eco.confirm({
      title: "Delete this record?",
      message: "It will be removed from your totals and your recycling rate.",
      confirmText: "Delete",
      danger: true,
    });
    if (!ok) return;
    const res = await Eco.api("/api/recycling/" + id, { method: "DELETE" });
    if (!res.success) { Eco.toast(res.error, "error", "Could not delete"); return; }
    Eco.toast(res.message, "success", "Deleted");
    load();
  }

  Eco.$("#recyclingForm").addEventListener("submit", async function (e) {
    e.preventDefault();
    Eco.$("#quantityError").textContent = "";

    const quantity = parseFloat(Eco.$("#quantity").value);
    if (!quantity || quantity <= 0) {
      Eco.$("#quantityError").textContent = "Please enter a valid positive quantity.";
      return;
    }

    const btn = Eco.$("#saveRecycling");
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving…';

    const res = await Eco.api("/api/recycling", {
      method: "POST",
      body: {
        material: Eco.$("#material").value,
        quantity: quantity,
        unit: Eco.$("#unit").value,
        method: Eco.$("#method").value,
        notes: Eco.$("#notes").value,
        date: Eco.$("#date").value,
      },
    });

    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Save record';

    if (!res.success) { Eco.toast(res.error, "error", "Could not save"); return; }

    Eco.toast(res.message + " Around " + res.co2_saved + " kg CO₂e avoided.", "success", "Recycling logged");
    Eco.$("#ecoPointsTop").textContent = Number(res.eco_points).toLocaleString();
    Eco.closeModal("recyclingModal");
    Eco.$("#recyclingForm").reset();
    load();
  });

  ["#filterMaterial", "#filterFrom", "#filterTo"].forEach(function (sel) {
    Eco.$(sel).addEventListener("input", renderRecords);
  });
  Eco.$("#clearFilters").addEventListener("click", function () {
    ["#filterMaterial", "#filterFrom", "#filterTo"].forEach((s) => (Eco.$(s).value = ""));
    renderRecords();
  });

  async function load() {
    const res = await Eco.api("/api/recycling");
    if (!res.success) { Eco.toast(res.error, "error", "Could not load records"); return; }
    records = res.records;
    renderSummary(res.summary);
    renderCharts(res);
    renderGoals(res.goals);
    renderRecords();
  }

  document.addEventListener("DOMContentLoaded", function () {
    Eco.$("#date").value = new Date().toISOString().slice(0, 10);
    load();
  });
})();
