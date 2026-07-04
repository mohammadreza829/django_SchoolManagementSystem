/* =====================================================
   NOVA JS — موتور انیمیشن سبک و بدون وابستگی به CDN
   Reveal / Stagger / Counter / Tilt / Spotlight / Typewriter
   ===================================================== */
(function () {
  "use strict";
  var d = document, de = d.documentElement;
  var reduced = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (!reduced) de.classList.add("js");

  /* ---------- نوار پیشرفت اسکرول ---------- */
  var bar = d.getElementById("nv-progress");
  if (bar) {
    var onScroll = function () {
      var h = de.scrollHeight - window.innerHeight;
      bar.style.width = (h > 0 ? (window.scrollY / h) * 100 : 0) + "%";
    };
    addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  /* ---------- قیمت‌ها: جداکننده‌ی سه‌رقمی فارسی ---------- */
  d.querySelectorAll(".price-current, .price-original, [data-price]").forEach(function (el) {
    el.textContent = el.textContent.replace(/[0-9][0-9,]{3,}/g, function (n) {
      var num = Number(String(n).replace(/,/g, ""));
      return isNaN(num) ? n : num.toLocaleString("fa-IR");
    });
  });

  /* ---------- Reveal با IntersectionObserver ---------- */
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.classList.add("nv-in", "nv-play");
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.01, rootMargin: "0px 0px -36px 0px" });

    d.querySelectorAll("[data-reveal], [data-stagger], [data-chat-demo], .nv-io").forEach(function (el) {
      io.observe(el);
    });

    d.querySelectorAll("[data-stagger]").forEach(function (parent) {
      var items = parent.querySelectorAll("[data-item]");
      items.forEach(function (it, i) {
        it.style.setProperty("--nv-d", Math.min(i * 0.07, 0.9).toFixed(2) + "s");
      });
    });

    /* ---------- شمارنده‌ها (فارسی) ---------- */
    var fmt = function (v, dec) {
      return v.toLocaleString("fa-IR", { minimumFractionDigits: dec, maximumFractionDigits: dec });
    };
    var cio = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        cio.unobserve(e.target);
        var el = e.target;
        var target = parseFloat(el.dataset.counter || "0");
        var dec = parseInt(el.dataset.decimals || "0", 10);
        var suf = el.dataset.suffix || "";
        if (reduced) { el.textContent = fmt(target, dec) + suf; return; }
        var t0 = null;
        var step = function (ts) {
          if (!t0) t0 = ts;
          var p = Math.min((ts - t0) / 1600, 1);
          p = 1 - Math.pow(1 - p, 3); /* easeOutCubic */
          el.textContent = fmt(target * p, dec) + suf;
          if (p < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
      });
    }, { threshold: 0.4 });
    d.querySelectorAll("[data-counter]").forEach(function (el) { cio.observe(el); });
  } else {
    de.classList.remove("js");
  }

  /* ---------- تور ایمنی: هر چیزی که رصد نشد بعد ۲.۵ ثانیه نمایان شود ---------- */
  setTimeout(function () {
    d.querySelectorAll("[data-reveal]:not(.nv-in), [data-stagger]:not(.nv-in), [data-chat-demo]:not(.nv-in)").forEach(function (el) {
      if (el.getBoundingClientRect().top < innerHeight + 150) el.classList.add("nv-in", "nv-play");
    });
  }, 2500);

  /* ---------- سلامِ گوی دستیار ---------- */
  var fab = d.querySelector(".nv-fab");
  if (fab) {
    setTimeout(function () {
      fab.classList.add("nv-fab-hi");
      setTimeout(function () { fab.classList.remove("nv-fab-hi"); }, 4500);
    }, 1400);
  }

  if (reduced) return; /* بقیه فقط افکت تزیینی است */

  /* ---------- اسپات‌لایت دنبال موس ---------- */
  d.addEventListener("pointermove", function (ev) {
    var el = ev.target.closest ? ev.target.closest(".nv-cell, .course-card") : null;
    if (!el) return;
    var r = el.getBoundingClientRect();
    el.style.setProperty("--mx", (ev.clientX - r.left) + "px");
    el.style.setProperty("--my", (ev.clientY - r.top) + "px");
  }, { passive: true });

  /* ---------- تیلت سه‌بعدی ---------- */
  d.querySelectorAll("[data-tilt]").forEach(function (el) {
    el.addEventListener("pointermove", function (ev) {
      var r = el.getBoundingClientRect();
      var x = (ev.clientX - r.left) / r.width - 0.5;
      var y = (ev.clientY - r.top) / r.height - 0.5;
      el.style.transform = "perspective(950px) rotateY(" + (x * 6).toFixed(2) + "deg) rotateX(" + (-y * 6).toFixed(2) + "deg)";
    });
    el.addEventListener("pointerleave", function () {
      el.style.transform = "";
    });
  });

  /* ---------- دکمه‌ی مگنتی ---------- */
  d.querySelectorAll("[data-magnet]").forEach(function (el) {
    el.addEventListener("pointermove", function (ev) {
      var r = el.getBoundingClientRect();
      var dx = (ev.clientX - r.left - r.width / 2) * 0.16;
      var dy = (ev.clientY - r.top - r.height / 2) * 0.22;
      el.style.transform = "translate(" + dx.toFixed(1) + "px," + dy.toFixed(1) + "px)";
    });
    el.addEventListener("pointerleave", function () { el.style.transform = ""; });
  });

  /* ---------- تایپ‌رایتر ---------- */
  d.querySelectorAll("[data-type]").forEach(function (el) {
    var list;
    try { list = JSON.parse(el.dataset.type); } catch (e) { list = [el.dataset.type]; }
    if (!Array.isArray(list)) list = [String(list)];
    list = list.filter(function (s) { return s && String(s).trim(); });
    if (!list.length) { el.classList.remove("nv-caret"); return; }
    var wi = 0, ci = 0, deleting = false;
    (function tick() {
      var w = String(list[wi]);
      if (!deleting) {
        ci++;
        el.textContent = w.slice(0, ci);
        if (ci === w.length) {
          if (list.length === 1) return; /* یک عبارت: ثابت بماند */
          deleting = true;
          return void setTimeout(tick, 2000);
        }
      } else {
        ci--;
        el.textContent = w.slice(0, ci);
        if (ci === 0) { deleting = false; wi = (wi + 1) % list.length; }
      }
      setTimeout(tick, deleting ? 34 : 82);
    })();
  });
})();
