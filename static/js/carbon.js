/* =========================================================================
   carbon.js — runs the calculator and renders the footprint breakdown.
   ========================================================================= */

(function () {
  "use strict";

  const Eco = window.Eco;
  const SOURCE_META = {
    electricity: { label: "Electricity", icon: "bolt", color: Eco.chartPalette.amber },
    transport: { label: "Transport", icon: "car", color: Eco.chartPalette.sky },
    food: { label: "Food", icon: "utensils", color: Eco.chartPalette.leaf },
    waste: { label: "Waste", icon: "trash-can", color: Eco.chartPalette.earth },
  };

  function readForm() {
    return {
      electricity: Eco.$("#electricity").value,
      transport_type: Eco.$("#transportType").value,
      transport_distance: Eco.$("#distance").value,
      veg_meals: Eco.$("#vegMeals").value,
      nonveg_meals: Eco.$("#nonvegMeals").value,
      plastic_waste: Eco.$("#plasticWaste").value,
      organic_waste: Eco.$("#organicWaste").value,
      paper_waste: Eco.$("#paperWaste").value,
      save: Eco.$("#saveAssessment").checked,
    };
  }

  function renderResult(result) {
    Eco.countTo(Eco.$("#monthlyTotal"), result.monthly_total, { decimals: 1 });
    Eco.$("#annualTotal").textContent = Eco.number(result.annual_total, 0);
    Eco.$("#perDay").textContent = Eco.number(result.per_day, 1);
    Eco.$("#trees").textContent = Eco.number(result.trees_equivalent, 0);

    const chip = Eco.$("#changeChip");
    if (result.change_pct === null || result.change_pct === undefined) {
      chip.textContent = "First assessment";
      chip.className = "muted small";
    } else {
      const down = result.change_pct < 0;
      chip.className = "chip " + (down ? "chip-completed" : "chip-high");
      chip.innerHTML =
        '<i class="fa-solid fa-arrow-trend-' + (down ? "down" : "up") + '"></i> ' +
        Math.abs(result.change_pct).toFixed(1) + "% vs last assessment";
    }

    const values = Object.keys(result.breakdown)
      .map((k) => ({ label: SOURCE_META[k].label, value: result.breakdown[k], color: SOURCE_META[k].color }))
      .filter((v) => v.value > 0);

    if (values.length) Eco.doughnutChart("breakdownChart", values);
    else Eco.chartEmpty("breakdownChart", "Enter at least one value to see a breakdown.");

    const total = result.monthly_total || 1;
    Eco.$("#breakdownList").innerHTML = Object.keys(result.breakdown).map(function (key) {
      const meta = SOURCE_META[key];
      const value = result.breakdown[key];
      const pct = (value / total) * 100;
      return (
        '<div class="pillar">' +
        '<div class="pillar-top"><span><i class="fa-solid fa-' + meta.icon + '"></i> ' +
        meta.label + "</span><span>" + Eco.number(value, 1) + " kg · " + pct.toFixed(0) + "%</span></div>" +
        '<div class="bar"><span data-fill="' + pct + '"></span></div></div>'
      );
    }).join("") +
      (result.largest_source
        ? '<p class="small muted" style="margin-top:12px">Your largest source is <strong>' +
          Eco.escape(SOURCE_META[result.largest_source].label) +
          "</strong>. Start there for the biggest reduction.</p>"
        : "");

    Eco.$$("[data-fill]", Eco.$("#breakdownList")).forEach((s) => Eco.setBar(s, s.getAttribute("data-fill")));
  }

  Eco.$("#carbonForm").addEventListener("submit", async function (e) {
    e.preventDefault();
    const btn = Eco.$("#calcBtn");
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Calculating…';

    const res = await Eco.api("/api/carbon/calculate", { method: "POST", body: readForm() });

    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-calculator"></i> Calculate footprint';

    if (!res.success) { Eco.toast(res.error, "error", "Could not calculate"); return; }

    renderResult(res.result);
    Eco.toast(res.message, "success", "Estimate ready");
    if (res.points_awarded) {
      Eco.$("#ecoPointsTop").textContent = Number(res.eco_points).toLocaleString();
      loadHistory();
    }
  });

  function renderHistory(records) {
    const list = Eco.$("#historyList");
    if (!records.length) {
      list.innerHTML = Eco.emptyState({
        icon: "smog",
        title: "No assessments saved yet",
        message: "Fill in the form and calculate to store your first monthly estimate.",
      });
      Eco.chartEmpty("historyChart", "Save an assessment to build your history.");
      return;
    }

    const ordered = records.slice().reverse();
    Eco.lineChart("historyChart",
      ordered.map((r) => Eco.date(r.created_at)),
      [{ label: "kg CO₂e", data: ordered.map((r) => r.total_emissions), color: Eco.chartPalette.coral }]);

    list.innerHTML = records.slice(0, 8).map(function (r) {
      return (
        '<div class="list-row"><div class="rec-icon"><i class="fa-solid fa-smog"></i></div>' +
        '<div class="grow"><h4>' + Eco.number(r.total_emissions, 1) + " kg CO₂e</h4>" +
        "<p>" + Eco.date(r.created_at) + " · " + Eco.number(r.electricity, 0) + " kWh · " +
        Eco.number(r.transport_distance, 0) + " km</p></div>" +
        '<span class="chip">' + Eco.escape(Eco.titleCase((r.transport_type || "").replace("_", " "))) +
        "</span></div>"
      );
    }).join("");
  }

  async function loadHistory() {
    const res = await Eco.api("/api/carbon");
    if (!res.success) { Eco.toast(res.error, "error", "Could not load history"); return; }
    renderHistory(res.records);

    // Pre-fill the form from the most recent assessment so updating is quick.
    if (res.latest) {
      Eco.$("#electricity").value = res.latest.electricity;
      Eco.$("#transportType").value = res.latest.transport_type || "petrol_car";
      Eco.$("#distance").value = res.latest.transport_distance;
      Eco.$("#vegMeals").value = res.latest.veg_meals;
      Eco.$("#nonvegMeals").value = res.latest.nonveg_meals;
    }
  }

  document.addEventListener("DOMContentLoaded", loadHistory);
})();
