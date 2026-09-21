/* =========================================================================
   charts.js — thin wrappers around Chart.js so every chart in the app shares
   one visual language and one set of responsive defaults.
   ========================================================================= */

(function () {
  "use strict";

  const Eco = window.Eco || (window.Eco = {});
  const registry = {};   // canvasId -> Chart instance

  const PALETTE = {
    leaf: "#2ea36a",
    leafDark: "#1d7a4c",
    leafLight: "#7fd3a6",
    sky: "#2f80c4",
    amber: "#e0a63c",
    coral: "#d9614c",
    earth: "#b99a72",
    slate: "#6b7d74",
  };

  const CATEGORY_COLORS = {
    Plastic: PALETTE.sky,
    Paper: PALETTE.amber,
    Glass: PALETTE.leafLight,
    Metal: PALETTE.slate,
    Organic: PALETTE.leaf,
    "E-Waste": PALETTE.coral,
    Textile: PALETTE.earth,
    Other: "#a3b2aa",
  };

  Eco.chartPalette = PALETTE;
  Eco.categoryColor = (name) => CATEGORY_COLORS[name] || PALETTE.leaf;

  function baseOptions(extra) {
    const grid = getComputedStyle(document.documentElement)
      .getPropertyValue("--border").trim() || "#dce9e1";
    const ink = getComputedStyle(document.documentElement)
      .getPropertyValue("--ink-500").trim() || "#6b7d74";

    return Object.assign({
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 900, easing: "easeOutQuart" },
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          display: false,
          labels: { usePointStyle: true, boxWidth: 8, color: ink, font: { size: 11 } },
        },
        tooltip: {
          backgroundColor: "#0f3d2a",
          padding: 11,
          cornerRadius: 10,
          titleFont: { size: 12 },
          bodyFont: { size: 12 },
          displayColors: true,
          boxPadding: 4,
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: ink, font: { size: 11 } } },
        y: {
          beginAtZero: true,
          grid: { color: grid, drawBorder: false },
          ticks: { color: ink, font: { size: 11 }, maxTicksLimit: 6 },
        },
      },
    }, extra || {});
  }

  function destroy(canvasId) {
    if (registry[canvasId]) {
      registry[canvasId].destroy();
      delete registry[canvasId];
    }
  }
  Eco.destroyChart = destroy;

  function context(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;
    destroy(canvasId);
    // Clear any "no data" overlay left from a previous render.
    const overlay = canvas.parentElement.querySelector("[data-chart-empty]");
    if (overlay) overlay.remove();
    canvas.style.display = "";
    return canvas.getContext("2d");
  }

  function gradient(ctx, hex) {
    const g = ctx.createLinearGradient(0, 0, 0, 260);
    g.addColorStop(0, hex + "55");
    g.addColorStop(1, hex + "05");
    return g;
  }

  /** Bar chart. datasets: [{label, data, color}] */
  Eco.barChart = function (canvasId, labels, datasets, options) {
    const ctx = context(canvasId);
    if (!ctx) return null;
    registry[canvasId] = new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: datasets.map((d) => ({
          label: d.label,
          data: d.data,
          backgroundColor: d.color || PALETTE.leaf,
          borderRadius: 7,
          borderSkipped: false,
          maxBarThickness: 40,
        })),
      },
      options: baseOptions(Object.assign({
        plugins: { legend: { display: datasets.length > 1, position: "bottom",
          labels: { usePointStyle: true, boxWidth: 8 } } },
      }, options)),
    });
    return registry[canvasId];
  };

  /** Line / area chart. datasets: [{label, data, color, fill}] */
  Eco.lineChart = function (canvasId, labels, datasets, options) {
    const ctx = context(canvasId);
    if (!ctx) return null;
    registry[canvasId] = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: datasets.map((d) => ({
          label: d.label,
          data: d.data,
          borderColor: d.color || PALETTE.leaf,
          backgroundColor: d.fill === false ? "transparent" : gradient(ctx, d.color || PALETTE.leaf),
          fill: d.fill !== false,
          tension: 0.38,
          borderWidth: 2.5,
          pointRadius: 3,
          pointHoverRadius: 6,
          pointBackgroundColor: "#fff",
          pointBorderColor: d.color || PALETTE.leaf,
          pointBorderWidth: 2,
        })),
      },
      options: baseOptions(Object.assign({
        plugins: { legend: { display: datasets.length > 1, position: "bottom",
          labels: { usePointStyle: true, boxWidth: 8 } } },
      }, options)),
    });
    return registry[canvasId];
  };

  /** Doughnut chart. values: [{label, value, color}] */
  Eco.doughnutChart = function (canvasId, values, options) {
    const ctx = context(canvasId);
    if (!ctx) return null;
    registry[canvasId] = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: values.map((v) => v.label),
        datasets: [{
          data: values.map((v) => v.value),
          backgroundColor: values.map((v) => v.color || Eco.categoryColor(v.label)),
          borderWidth: 3,
          borderColor: getComputedStyle(document.documentElement)
            .getPropertyValue("--surface").trim() || "#fff",
          hoverOffset: 8,
        }],
      },
      options: Object.assign(baseOptions({
        cutout: "62%",
        scales: {},
        plugins: {
          legend: {
            display: true, position: "bottom",
            labels: { usePointStyle: true, boxWidth: 8, padding: 14, font: { size: 11 } },
          },
          tooltip: {
            backgroundColor: "#0f3d2a", padding: 11, cornerRadius: 10,
            callbacks: {
              label: function (item) {
                const total = item.dataset.data.reduce((a, b) => a + b, 0) || 1;
                const pct = ((item.raw / total) * 100).toFixed(1);
                return " " + item.label + ": " + item.raw + " (" + pct + "%)";
              },
            },
          },
        },
      }), options || {}),
    });
    return registry[canvasId];
  };

  /** Show a friendly message in place of an empty chart. */
  Eco.chartEmpty = function (canvasId, message) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    destroy(canvasId);
    canvas.style.display = "none";
    const box = canvas.parentElement;
    const existing = box.querySelector("[data-chart-empty]");
    if (existing) existing.remove();
    const overlay = document.createElement("div");
    overlay.setAttribute("data-chart-empty", "");
    overlay.className = "empty";
    overlay.style.padding = "24px 10px";
    overlay.innerHTML =
      '<div class="emoji"><i class="fa-solid fa-chart-simple"></i></div>' +
      "<p>" + Eco.escape(message || "No data for this period yet.") + "</p>";
    box.appendChild(overlay);
  };
})();
