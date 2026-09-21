/* =========================================================================
   main.js — shared utilities used by every page.
   Exposes a single global: window.Eco
   ========================================================================= */

(function () {
  "use strict";

  const Eco = {};

  /* ------------------------------------------------------------ helpers */
  Eco.$ = (selector, root) => (root || document).querySelector(selector);
  Eco.$$ = (selector, root) => Array.from((root || document).querySelectorAll(selector));

  Eco.escape = function (value) {
    if (value === null || value === undefined) return "";
    return String(value)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  };

  Eco.number = function (value, decimals) {
    const n = Number(value) || 0;
    return n.toLocaleString(undefined, {
      minimumFractionDigits: decimals || 0,
      maximumFractionDigits: decimals === undefined ? 1 : decimals,
    });
  };

  Eco.date = function (value) {
    if (!value) return "—";
    const d = new Date(value);
    if (isNaN(d.getTime())) return value;
    return d.toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" });
  };

  Eco.titleCase = (s) => (s || "").replace(/\b\w/g, (c) => c.toUpperCase());

  /* ------------------------------------------------------------ requests */
  /**
   * Fetch wrapper that always returns parsed JSON and never throws on a
   * handled API error. Sends JSON unless a FormData body is supplied.
   */
  Eco.api = async function (url, options) {
    const config = Object.assign({ method: "GET", headers: {} }, options || {});
    if (config.body && !(config.body instanceof FormData)) {
      config.headers["Content-Type"] = "application/json";
      config.body = JSON.stringify(config.body);
    }
    config.headers["Accept"] = "application/json";

    try {
      const response = await fetch(url, config);
      if (response.status === 401) {
        Eco.toast("Your session ended. Sign in again.", "error");
        setTimeout(() => (window.location.href = "/login"), 1200);
        return { success: false, error: "Not signed in." };
      }
      const contentType = response.headers.get("content-type") || "";
      if (!contentType.includes("application/json")) {
        return { success: false, error: "Something went wrong. Please try again." };
      }
      const data = await response.json();
      if (!response.ok && !data.error) data.error = "Something went wrong. Please try again.";
      return data;
    } catch (err) {
      console.error(err);
      return { success: false, error: "Network problem. Check your connection and retry." };
    }
  };

  /* -------------------------------------------------------------- toasts */
  Eco.toast = function (message, type, title) {
    let stack = Eco.$(".toast-stack");
    if (!stack) {
      stack = document.createElement("div");
      stack.className = "toast-stack";
      stack.setAttribute("role", "status");
      stack.setAttribute("aria-live", "polite");
      document.body.appendChild(stack);
    }

    const icons = { success: "circle-check", error: "circle-exclamation", warning: "triangle-exclamation", info: "circle-info" };
    const kind = type || "success";
    const el = document.createElement("div");
    el.className = "toast " + (kind === "success" ? "" : kind);
    el.innerHTML =
      '<i class="fa-solid fa-' + (icons[kind] || icons.info) + ' toast-icon"></i>' +
      '<div><strong>' + Eco.escape(title || Eco.titleCase(kind)) + "</strong>" +
      "<span>" + Eco.escape(message) + "</span></div>";
    stack.appendChild(el);

    setTimeout(() => {
      el.classList.add("leaving");
      setTimeout(() => el.remove(), 260);
    }, 4200);
  };

  /* -------------------------------------------------------------- modals */
  Eco.openModal = function (id) {
    const el = typeof id === "string" ? document.getElementById(id) : id;
    if (!el) return;
    el.classList.add("open");
    el.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    const focusable = el.querySelector("input, select, textarea, button");
    if (focusable) setTimeout(() => focusable.focus(), 120);
  };

  Eco.closeModal = function (id) {
    const el = typeof id === "string" ? document.getElementById(id) : id;
    if (!el) return;
    el.classList.remove("open");
    el.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  };

  /** Promise-based confirmation dialog built on the shared markup. */
  Eco.confirm = function (options) {
    return new Promise((resolve) => {
      const backdrop = document.getElementById("confirmModal");
      if (!backdrop) return resolve(window.confirm(options.message || "Are you sure?"));

      Eco.$("#confirmTitle").textContent = options.title || "Are you sure?";
      Eco.$("#confirmMessage").textContent = options.message || "";
      const okBtn = Eco.$("#confirmOk");
      okBtn.textContent = options.confirmText || "Confirm";
      okBtn.className = "btn " + (options.danger ? "btn-danger" : "btn-primary");

      const done = (value) => {
        Eco.closeModal(backdrop);
        okBtn.removeEventListener("click", onOk);
        Eco.$("#confirmCancel").removeEventListener("click", onCancel);
        resolve(value);
      };
      const onOk = () => done(true);
      const onCancel = () => done(false);

      okBtn.addEventListener("click", onOk);
      Eco.$("#confirmCancel").addEventListener("click", onCancel);
      Eco.openModal(backdrop);
    });
  };

  /* ---------------------------------------------------- loading / empty */
  Eco.skeleton = function (container, rows) {
    if (!container) return;
    let html = "";
    for (let i = 0; i < (rows || 3); i++) {
      html += '<div class="skeleton skeleton-line" style="width:' + (60 + (i % 3) * 14) + '%"></div>';
    }
    container.innerHTML = html;
  };

  Eco.emptyState = function (options) {
    return (
      '<div class="empty">' +
      '<div class="emoji"><i class="fa-solid fa-' + (options.icon || "leaf") + '"></i></div>' +
      "<h3>" + Eco.escape(options.title) + "</h3>" +
      "<p>" + Eco.escape(options.message) + "</p>" +
      (options.action
        ? '<button class="btn btn-primary" data-empty-action="' + Eco.escape(options.action.id) + '">' +
          '<i class="fa-solid fa-plus"></i>' + Eco.escape(options.action.label) + "</button>"
        : "") +
      "</div>"
    );
  };

  /* ---------------------------------------------------------- app chrome */
  function initChrome() {
    // Sidebar for small screens
    const sidebar = Eco.$("#sidebar");
    const backdrop = Eco.$("#sidebarBackdrop");
    const toggle = Eco.$("#sidebarToggle");

    if (toggle && sidebar) {
      toggle.addEventListener("click", () => {
        const open = sidebar.classList.toggle("open");
        if (backdrop) backdrop.classList.toggle("open", open);
        toggle.setAttribute("aria-expanded", String(open));
      });
    }
    if (backdrop) {
      backdrop.addEventListener("click", () => {
        sidebar.classList.remove("open");
        backdrop.classList.remove("open");
        if (toggle) toggle.setAttribute("aria-expanded", "false");
      });
    }

    // Dropdowns (notifications, profile menu)
    Eco.$$("[data-dropdown]").forEach((trigger) => {
      const menu = document.getElementById(trigger.getAttribute("data-dropdown"));
      if (!menu) return;
      trigger.addEventListener("click", (e) => {
        e.stopPropagation();
        const open = !menu.classList.contains("open");
        Eco.$$(".dropdown.open").forEach((d) => d.classList.remove("open"));
        menu.classList.toggle("open", open);
        trigger.setAttribute("aria-expanded", String(open));
      });
    });
    document.addEventListener("click", () => {
      Eco.$$(".dropdown.open").forEach((d) => d.classList.remove("open"));
    });

    // Modal chrome: backdrop click, [data-close] buttons, Escape
    Eco.$$(".modal-backdrop").forEach((el) => {
      el.addEventListener("click", (e) => { if (e.target === el) Eco.closeModal(el); });
    });
    Eco.$$("[data-close-modal]").forEach((btn) => {
      btn.addEventListener("click", () => Eco.closeModal(btn.getAttribute("data-close-modal")));
    });
    Eco.$$("[data-open-modal]").forEach((btn) => {
      btn.addEventListener("click", () => Eco.openModal(btn.getAttribute("data-open-modal")));
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") Eco.$$(".modal-backdrop.open").forEach((m) => Eco.closeModal(m));
    });

    // Logout
    const logout = Eco.$("#logoutBtn");
    if (logout) {
      logout.addEventListener("click", async (e) => {
        e.preventDefault();
        const ok = await Eco.confirm({
          title: "Sign out?",
          message: "You will need to sign in again to reach your dashboard.",
          confirmText: "Sign out",
        });
        if (!ok) return;
        const res = await Eco.api("/api/logout", { method: "POST" });
        window.location.href = res.redirect || "/";
      });
    }

    // Global search jumps to the matching module
    const search = Eco.$("#globalSearch");
    if (search) {
      const routes = [
        { keys: ["dashboard", "home", "overview"], url: "/dashboard" },
        { keys: ["waste", "analyzer", "plastic", "garbage"], url: "/waste" },
        { keys: ["carbon", "footprint", "emission", "co2"], url: "/carbon" },
        { keys: ["recycle", "recycling"], url: "/recycling" },
        { keys: ["goal", "zero", "planner"], url: "/zero-waste" },
        { keys: ["bio", "species", "bird", "plant"], url: "/biodiversity" },
        { keys: ["challenge", "points", "badge"], url: "/challenges" },
        { keys: ["report", "pdf", "summary"], url: "/reports" },
        { keys: ["profile", "settings", "password", "theme"], url: "/profile" },
      ];
      search.addEventListener("keydown", (e) => {
        if (e.key !== "Enter") return;
        const term = search.value.trim().toLowerCase();
        if (!term) return;
        const hit = routes.find((r) => r.keys.some((k) => k.includes(term) || term.includes(k)));
        if (hit) window.location.href = hit.url;
        else Eco.toast('No module matches "' + term + '". Try "waste" or "carbon".', "warning", "No match");
      });
    }
  }

  /** Apply the saved theme immediately so pages never flash the wrong colours. */
  Eco.applyTheme = function (theme) {
    document.documentElement.setAttribute("data-theme", theme === "dark" ? "dark" : "light");
  };

  document.addEventListener("DOMContentLoaded", initChrome);
  window.Eco = Eco;
})();
