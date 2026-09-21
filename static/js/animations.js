/* =========================================================================
   animations.js — counters, progress bars, score rings and scroll reveals.
   Every helper respects prefers-reduced-motion.
   ========================================================================= */

(function () {
  "use strict";

  const Eco = window.Eco || (window.Eco = {});
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function easeOutCubic(t) { return 1 - Math.pow(1 - t, 3); }

  /**
   * Count an element up to a target value.
   * Reads data-decimals, data-prefix and data-suffix when present.
   */
  Eco.countTo = function (el, target, options) {
    if (!el) return;
    const config = options || {};
    const decimals = config.decimals !== undefined
      ? config.decimals
      : Number(el.dataset.decimals || 0);
    const prefix = config.prefix || el.dataset.prefix || "";
    const suffix = config.suffix || el.dataset.suffix || "";
    const duration = config.duration || 1100;
    const to = Number(target) || 0;

    const render = (value) =>
      (el.textContent = prefix + value.toLocaleString(undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      }) + suffix);

    if (reduceMotion) return render(to);

    const from = Number(el.dataset.current || 0);
    const start = performance.now();

    function frame(now) {
      const progress = Math.min((now - start) / duration, 1);
      render(from + (to - from) * easeOutCubic(progress));
      if (progress < 1) requestAnimationFrame(frame);
      else el.dataset.current = String(to);
    }
    requestAnimationFrame(frame);
  };

  /** Animate every [data-count] element inside a root. */
  Eco.animateCounters = function (root) {
    Eco.$$("[data-count]", root || document).forEach((el) => {
      Eco.countTo(el, el.getAttribute("data-count"));
    });
  };

  /** Fill a .bar > span to a percentage. */
  Eco.setBar = function (el, percent) {
    if (!el) return;
    const span = el.matches(".bar") ? el.querySelector("span") : el;
    if (!span) return;
    const value = Math.max(0, Math.min(Number(percent) || 0, 100));
    if (reduceMotion) { span.style.width = value + "%"; return; }
    span.style.width = "0%";
    requestAnimationFrame(() => setTimeout(() => (span.style.width = value + "%"), 60));
  };

  /**
   * Draw a circular progress ring.
   * `circle` must be an SVG <circle> whose radius is known.
   */
  Eco.setRing = function (circle, percent, radius) {
    if (!circle) return;
    const r = radius || Number(circle.getAttribute("r")) || 70;
    const circumference = 2 * Math.PI * r;
    const value = Math.max(0, Math.min(Number(percent) || 0, 100));
    circle.style.strokeDasharray = circumference + " " + circumference;
    circle.style.strokeDashoffset = String(circumference);
    const target = circumference - (value / 100) * circumference;
    if (reduceMotion) { circle.style.strokeDashoffset = String(target); return; }
    requestAnimationFrame(() => setTimeout(() => (circle.style.strokeDashoffset = String(target)), 120));
  };

  /** Reveal elements as they scroll into view (landing page sections). */
  Eco.revealOnScroll = function (selector) {
    const items = Eco.$$(selector || "[data-reveal]");
    if (!items.length) return;
    if (reduceMotion || !("IntersectionObserver" in window)) {
      items.forEach((el) => el.classList.add("fade-up"));
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry, index) => {
        if (!entry.isIntersecting) return;
        setTimeout(() => entry.target.classList.add("fade-up"), index * 70);
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.16 });
    items.forEach((el) => observer.observe(el));
  };

  /** Run counters once their section scrolls into view. */
  Eco.countersOnScroll = function (selector) {
    const items = Eco.$$(selector || "[data-count-scroll]");
    if (!items.length) return;
    if (!("IntersectionObserver" in window)) {
      items.forEach((el) => Eco.countTo(el, el.getAttribute("data-count-scroll")));
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        Eco.countTo(entry.target, entry.target.getAttribute("data-count-scroll"));
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.4 });
    items.forEach((el) => observer.observe(el));
  };

  document.addEventListener("DOMContentLoaded", function () {
    Eco.revealOnScroll();
    Eco.countersOnScroll();
  });
})();
