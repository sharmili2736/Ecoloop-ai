/* =========================================================================
   waste.js — upload, classify, save and filter waste records.
   ========================================================================= */

(function () {
  "use strict";

  const Eco = window.Eco;
  let records = [];
  let lastResult = null;

  /* ------------------------------------------------------------ upload */
  const dropzone = Eco.$("#dropzone");
  const fileInput = Eco.$("#imageInput");
  const preview = Eco.$("#imagePreview");

  function showPreview(file) {
    if (!file) return;
    if (!/^image\//.test(file.type)) {
      Eco.toast("Please upload a supported image format.", "error", "Unsupported file");
      fileInput.value = "";
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      Eco.toast("That file is larger than the 5 MB limit.", "error", "File too large");
      fileInput.value = "";
      return;
    }
    const reader = new FileReader();
    reader.onload = function (e) {
      preview.src = e.target.result;
      preview.hidden = false;
    };
    reader.readAsDataURL(file);
  }

  dropzone.addEventListener("click", () => fileInput.click());
  dropzone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInput.click(); }
  });
  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault(); dropzone.classList.add("dragover");
  });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files.length) {
      fileInput.files = e.dataTransfer.files;
      showPreview(e.dataTransfer.files[0]);
    }
  });
  fileInput.addEventListener("change", () => showPreview(fileInput.files[0]));

  /* ----------------------------------------------------------- analyse */
  Eco.$("#analyzeForm").addEventListener("submit", async function (e) {
    e.preventDefault();
    Eco.$("#quantityError").textContent = "";

    const category = Eco.$("#categorySelect").value;
    const quantity = parseFloat(Eco.$("#quantityInput").value);
    const unit = Eco.$("#unitSelect").value;

    if (!category && !fileInput.files.length) {
      Eco.toast("Upload an image or pick a waste category.", "error", "Nothing to analyse");
      return;
    }
    if (!quantity || quantity <= 0) {
      Eco.$("#quantityError").textContent = "Please enter a valid positive quantity.";
      return;
    }

    const btn = Eco.$("#analyzeBtn");
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analysing…';
    Eco.skeleton(Eco.$("#resultBody"), 4);

    const form = new FormData();
    if (fileInput.files.length) form.append("image", fileInput.files[0]);
    if (category) form.append("category", category);
    form.append("quantity", quantity);
    form.append("unit", unit);

    const res = await Eco.api("/api/waste/analyze", { method: "POST", body: form });

    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Analyse';

    if (!res.success) {
      Eco.toast(res.error, "error", "Analysis failed");
      renderEmptyResult();
      return;
    }

    lastResult = res;
    renderResult(res);
    Eco.toast("Material identified as " + res.result.material + ".", "success", "Analysed");
  });

  function renderEmptyResult() {
    Eco.$("#resultBody").innerHTML =
      '<div class="empty"><div class="emoji"><i class="fa-solid fa-magnifying-glass-chart"></i></div>' +
      "<h3>Nothing analysed yet</h3><p>Add an image or choose a category, then press Analyse.</p></div>";
  }

  function renderResult(res) {
    const r = res.result;
    const impact = res.impact;
    const circumference = 2 * Math.PI * 30;

    Eco.$("#resultBody").innerHTML =
      '<div class="result-head">' +
      '<div class="confidence-ring"><svg width="74" height="74" viewBox="0 0 74 74">' +
      '<circle cx="37" cy="37" r="30" fill="none" stroke="var(--border)" stroke-width="7"/>' +
      '<circle id="confRing" cx="37" cy="37" r="30" fill="none" stroke="var(--leaf-500)" ' +
      'stroke-width="7" stroke-linecap="round" style="stroke-dasharray:' + circumference +
      ";stroke-dashoffset:" + circumference + ';transition:stroke-dashoffset 1s ease"/>' +
      '</svg><span class="val">' + r.confidence + "%</span></div>" +
      "<div><div class=\"small muted\">Detected material</div>" +
      '<div class="big">' + Eco.escape(r.material) + "</div>" +
      '<span class="chip chip-low" style="margin-top:6px">' + Eco.escape(r.classification) + "</span></div></div>" +

      '<p><strong>Recommended action.</strong> ' + Eco.escape(r.action) + "</p>" +

      '<div class="impact-list">' +
      '<div><div class="v">' + Eco.number(impact.recyclable_weight, 2) + ' kg</div><div class="k">Recyclable weight</div></div>' +
      '<div><div class="v">' + Eco.number(impact.landfill_diverted, 2) + ' kg</div><div class="k">Landfill diverted</div></div>' +
      '<div><div class="v">' + Eco.number(impact.co2_saved, 2) + ' kg</div><div class="k">Est. CO₂ saved</div></div>' +
      "</div>" +

      '<div class="demo-flag" style="margin-top:16px"><i class="fa-solid fa-circle-info"></i>' +
      "<div>" + Eco.escape(r.note) + " Confidence is a simulated value in demo mode.</div></div>" +

      '<div style="display:flex;gap:10px;margin-top:16px;flex-wrap:wrap">' +
      '<button class="btn btn-primary" id="saveRecordBtn"><i class="fa-solid fa-floppy-disk"></i> Save record (+5 points)</button>' +
      '<button class="btn btn-secondary" id="discardBtn">Discard</button></div>';

    // Animate the confidence ring once it is in the DOM.
    const ring = Eco.$("#confRing");
    setTimeout(() => {
      ring.style.strokeDashoffset = String(circumference - (r.confidence / 100) * circumference);
    }, 100);

    Eco.$("#saveRecordBtn").addEventListener("click", saveRecord);
    Eco.$("#discardBtn").addEventListener("click", function () {
      lastResult = null;
      renderEmptyResult();
    });
  }

  async function saveRecord() {
    if (!lastResult) return;
    const btn = Eco.$("#saveRecordBtn");
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving…';

    const res = await Eco.api("/api/waste", {
      method: "POST",
      body: {
        category: lastResult.result.category,
        material: lastResult.result.material,
        quantity: lastResult.quantity,
        unit: lastResult.unit,
        image_path: lastResult.image_path,
        ai_result: lastResult.result.classification,
        confidence: lastResult.result.confidence / 100,
      },
    });

    if (!res.success) {
      Eco.toast(res.error, "error", "Could not save");
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Save record (+5 points)';
      return;
    }

    Eco.toast(res.message, "success", "Saved");
    Eco.$("#ecoPointsTop").textContent = Number(res.eco_points).toLocaleString();
    lastResult = null;
    resetForm();
    renderEmptyResult();
    loadRecords();
  }

  function resetForm() {
    Eco.$("#analyzeForm").reset();
    fileInput.value = "";
    preview.hidden = true;
    preview.removeAttribute("src");
  }
  Eco.$("#resetBtn").addEventListener("click", function () {
    resetForm();
    renderEmptyResult();
  });

  /* ----------------------------------------------------------- records */
  function renderRecords() {
    const area = Eco.$("#recordsArea");
    const term = Eco.$("#filterSearch").value.trim().toLowerCase();
    const category = Eco.$("#filterCategory").value;
    const from = Eco.$("#filterFrom").value;
    const to = Eco.$("#filterTo").value;

    const filtered = records.filter(function (r) {
      if (category && r.category !== category) return false;
      if (term && !((r.material || "") + " " + r.category).toLowerCase().includes(term)) return false;
      const day = (r.created_at || "").slice(0, 10);
      if (from && day < from) return false;
      if (to && day > to) return false;
      return true;
    });

    if (!records.length) {
      area.innerHTML = Eco.emptyState({
        icon: "trash-can",
        title: "No waste records yet",
        message: "Analyse your first item above. Each saved record earns you 5 eco points.",
      });
      return;
    }
    if (!filtered.length) {
      area.innerHTML = Eco.emptyState({
        icon: "filter-circle-xmark",
        title: "Nothing matches those filters",
        message: "Try a different category or widen the date range.",
      });
      return;
    }

    area.innerHTML =
      '<div class="table-wrap"><table class="data"><thead><tr>' +
      "<th>Item</th><th>Category</th><th>Quantity</th><th>Confidence</th><th>Date</th><th></th>" +
      "</tr></thead><tbody>" +
      filtered.map(function (r) {
        const image = r.image_path
          ? '<img class="thumb" src="/static/' + Eco.escape(r.image_path) + '" alt="">'
          : '<div class="thumb" style="display:grid;place-items:center;color:var(--ink-300)">' +
            '<i class="fa-solid fa-image"></i></div>';
        return (
          "<tr>" +
          '<td><div style="display:flex;align-items:center;gap:11px">' + image +
          "<div><strong>" + Eco.escape(r.material || r.category) + "</strong><div class=\"small muted\">" +
          Eco.escape(r.ai_result || "") + "</div></div></div></td>" +
          '<td><span class="chip">' + Eco.escape(r.category) + "</span></td>" +
          "<td>" + Eco.number(r.quantity, 2) + " " + Eco.escape(r.unit) + "</td>" +
          "<td>" + (r.confidence ? (r.confidence * 100).toFixed(0) + "%" : "—") + "</td>" +
          "<td>" + Eco.date(r.created_at) + "</td>" +
          '<td class="text-right"><button class="icon-btn" data-delete="' + r.id +
          '" aria-label="Delete record"><i class="fa-solid fa-trash"></i></button></td></tr>'
        );
      }).join("") +
      "</tbody></table></div>";

    Eco.$$("[data-delete]", area).forEach(function (btn) {
      btn.addEventListener("click", () => deleteRecord(btn.getAttribute("data-delete")));
    });
  }

  async function deleteRecord(id) {
    const ok = await Eco.confirm({
      title: "Delete this record?",
      message: "The entry will be removed from your waste history and totals.",
      confirmText: "Delete",
      danger: true,
    });
    if (!ok) return;

    const res = await Eco.api("/api/waste/" + id, { method: "DELETE" });
    if (!res.success) { Eco.toast(res.error, "error", "Could not delete"); return; }
    Eco.toast(res.message, "success", "Deleted");
    loadRecords();
  }

  async function loadRecords() {
    const res = await Eco.api("/api/waste");
    if (!res.success) { Eco.toast(res.error, "error", "Could not load records"); return; }
    records = res.records;
    Eco.$("#wasteCount").textContent = res.summary.records;
    renderRecords();
  }

  ["#filterSearch", "#filterCategory", "#filterFrom", "#filterTo"].forEach(function (sel) {
    Eco.$(sel).addEventListener("input", renderRecords);
  });
  Eco.$("#clearFilters").addEventListener("click", function () {
    ["#filterSearch", "#filterCategory", "#filterFrom", "#filterTo"].forEach((s) => (Eco.$(s).value = ""));
    renderRecords();
  });

  document.addEventListener("DOMContentLoaded", loadRecords);
})();
