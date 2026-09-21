/* =========================================================================
   biodiversity.js — observation cards, sketch map and filtering.
   ========================================================================= */

(function () {
  "use strict";

  const Eco = window.Eco;
  const ICONS = {
    Bird: "dove", Plant: "seedling", Butterfly: "bug",
    Insect: "bug", Tree: "tree", "Small Animal": "paw",
  };
  let records = [];

  function filtered() {
    const term = Eco.$("#filterSpecies").value.trim().toLowerCase();
    const category = Eco.$("#filterCategory").value;
    const from = Eco.$("#filterFrom").value;
    const to = Eco.$("#filterTo").value;

    return records.filter(function (r) {
      if (category && r.category !== category) return false;
      if (term && !(r.species + " " + (r.location || "")).toLowerCase().includes(term)) return false;
      const day = r.observation_date || (r.created_at || "").slice(0, 10);
      if (from && day < from) return false;
      if (to && day > to) return false;
      return true;
    });
  }

  function renderCards() {
    const area = Eco.$("#cardsArea");
    const list = filtered();

    if (!records.length) {
      area.innerHTML = Eco.emptyState({
        icon: "dove",
        title: "No observations yet",
        message: "Start with whatever is outside your window — a tree, a bird, a bee.",
        action: { id: "addObs", label: "Add your first observation" },
      });
      const btn = area.querySelector('[data-empty-action="addObs"]');
      if (btn) btn.addEventListener("click", () => Eco.openModal("bioModal"));
      return;
    }
    if (!list.length) {
      area.innerHTML = Eco.emptyState({
        icon: "filter-circle-xmark",
        title: "Nothing matches those filters",
        message: "Try a different category or clear the date range.",
      });
      return;
    }

    area.innerHTML = '<div class="grid grid-3">' + list.map(function (r) {
      const media = r.image_path
        ? '<img src="/static/' + Eco.escape(r.image_path) + '" alt="' + Eco.escape(r.species) + '">'
        : '<i class="fa-solid fa-' + (ICONS[r.category] || "leaf") + '"></i>';
      return (
        '<article class="bio-card"><div class="bio-img">' + media + "</div>" +
        '<div class="bio-body">' +
        '<div style="display:flex;justify-content:space-between;gap:8px;align-items:flex-start">' +
        "<h4>" + Eco.escape(r.species) + "</h4>" +
        '<button class="icon-btn" style="width:30px;height:30px" data-delete="' + r.id +
        '" aria-label="Delete observation"><i class="fa-solid fa-trash" style="font-size:.75rem"></i></button></div>' +
        '<span class="chip">' + Eco.escape(r.category) + "</span>" +
        "<p><strong>" + Eco.escape(r.location || "Location not noted") + "</strong></p>" +
        "<p>" + Eco.escape(r.description || "No description added.") + "</p>" +
        '<p class="small muted"><i class="fa-regular fa-calendar"></i> ' +
        Eco.date(r.observation_date || r.created_at) + "</p>" +
        "</div></article>"
      );
    }).join("") + "</div>";

    Eco.$$("[data-delete]", area).forEach(function (btn) {
      btn.addEventListener("click", () => remove(btn.getAttribute("data-delete")));
    });
  }

  function renderMap() {
    const map = Eco.$("#sketchMap");
    Eco.$$(".map-pin", map).forEach((p) => p.remove());

    const list = filtered();
    list.forEach(function (r) {
      const pin = document.createElement("button");
      pin.className = "map-pin";
      pin.style.left = (r.map_x || 50) + "%";
      pin.style.top = (r.map_y || 50) + "%";
      pin.title = r.species + " — " + (r.location || "location not noted");
      pin.setAttribute("aria-label", pin.title);
      pin.innerHTML = '<i class="fa-solid fa-' + (ICONS[r.category] || "leaf") + '"></i>';
      pin.addEventListener("click", function () {
        Eco.toast(r.species + " · " + (r.location || "no location") + " · " +
          Eco.date(r.observation_date), "info", r.category);
      });
      map.appendChild(pin);
    });

    Eco.$("#mapLegend").innerHTML = Object.keys(ICONS).map(function (key) {
      return '<span><i class="fa-solid fa-' + ICONS[key] + '" style="color:var(--leaf-700)"></i> ' + key + "</span>";
    }).join("");

    if (!list.length) {
      const note = document.createElement("div");
      note.className = "map-pin";
      note.style.cssText = "left:50%;top:50%;width:auto;height:auto;border-radius:12px;padding:8px 14px;font-size:.8rem";
      note.textContent = "No observations to plot";
      map.appendChild(note);
    }
  }

  function renderChart(byCategory) {
    const keys = Object.keys(byCategory);
    if (!keys.length) {
      Eco.chartEmpty("categoryChart", "Add an observation to see the split.");
      return;
    }
    Eco.doughnutChart("categoryChart", keys.map(function (k) {
      return { label: k, value: byCategory[k] };
    }));
  }

  Eco.$("#bioForm").addEventListener("submit", async function (e) {
    e.preventDefault();
    Eco.$("#speciesError").textContent = "";

    const species = Eco.$("#species").value.trim();
    if (!species) { Eco.$("#speciesError").textContent = "Enter the species name."; return; }

    const file = Eco.$("#bioImage").files[0];
    if (file && file.size > 5 * 1024 * 1024) {
      Eco.toast("That file is larger than the 5 MB limit.", "error", "File too large");
      return;
    }

    const form = new FormData();
    form.append("species", species);
    form.append("category", Eco.$("#category").value);
    form.append("location", Eco.$("#location").value);
    form.append("observation_date", Eco.$("#observationDate").value);
    form.append("description", Eco.$("#description").value);
    if (file) form.append("image", file);

    const btn = Eco.$("#saveBio");
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving…';

    const res = await Eco.api("/api/biodiversity", { method: "POST", body: form });

    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Save observation';

    if (!res.success) { Eco.toast(res.error, "error", "Could not save"); return; }

    Eco.toast(res.message, "success", "Observation recorded");
    Eco.$("#ecoPointsTop").textContent = Number(res.eco_points).toLocaleString();
    Eco.closeModal("bioModal");
    Eco.$("#bioForm").reset();
    load();
  });

  async function remove(id) {
    const ok = await Eco.confirm({
      title: "Delete this observation?",
      message: "It will be removed from your records and the map.",
      confirmText: "Delete",
      danger: true,
    });
    if (!ok) return;
    const res = await Eco.api("/api/biodiversity/" + id, { method: "DELETE" });
    if (!res.success) { Eco.toast(res.error, "error", "Could not delete"); return; }
    Eco.toast(res.message, "success", "Deleted");
    load();
  }

  function refreshViews() { renderCards(); renderMap(); }

  ["#filterSpecies", "#filterCategory", "#filterFrom", "#filterTo"].forEach(function (sel) {
    Eco.$(sel).addEventListener("input", refreshViews);
  });
  Eco.$("#clearFilters").addEventListener("click", function () {
    ["#filterSpecies", "#filterCategory", "#filterFrom", "#filterTo"].forEach((s) => (Eco.$(s).value = ""));
    refreshViews();
  });

  async function load() {
    const res = await Eco.api("/api/biodiversity");
    if (!res.success) { Eco.toast(res.error, "error", "Could not load observations"); return; }
    records = res.records;

    Eco.countTo(Eco.$("#sumSpecies"), res.summary.species_observed, { decimals: 0 });
    Eco.countTo(Eco.$("#sumPlants"), res.summary.plants, { decimals: 0 });
    Eco.countTo(Eco.$("#sumBirds"), res.summary.birds, { decimals: 0 });
    Eco.countTo(Eco.$("#sumMonth"), res.summary.this_month, { decimals: 0 });
    Eco.$("#obsCount").textContent = res.summary.observations + " record" +
      (res.summary.observations === 1 ? "" : "s");

    renderChart(res.summary.by_category);
    refreshViews();
  }

  document.addEventListener("DOMContentLoaded", function () {
    Eco.$("#observationDate").value = new Date().toISOString().slice(0, 10);
    load();
  });
})();
