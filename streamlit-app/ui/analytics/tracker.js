/* =========================================================
 * Vitals self-hosted analytics — client tracker
 * ---------------------------------------------------------
 * Embedded inline (no CDN) so it works on closed networks.
 *
 * Transport:
 *   This script runs inside a streamlit.components.v1.html iframe.
 *   It uses window.Streamlit.setComponentValue() to push batches back
 *   to Python on each Streamlit rerun cycle. Python then bulk-inserts.
 *
 *   Because the script runs in the iframe, we hook events on
 *   window.parent.document where possible to capture clicks on the
 *   actual Streamlit page (the iframe is invisible / 0px).
 *
 *   We fall back to local-document hooks if cross-frame access is
 *   blocked (same-origin in Streamlit deployments — should work).
 *
 * Capture:
 *   - click       : every primary click (target text + position)
 *   - rage_click  : 3+ clicks on same element within 500ms
 *   - dead_click  : click on non-interactive node, no DOM mutation
 *                   within 250ms
 *   - scroll      : max scroll depth %, sampled on scrollend / unload
 *   - submit      : form submissions
 *   - error       : window.onerror + unhandledrejection
 *   - unload      : sends pageview duration and any pending batch
 *
 * Batching:
 *   - Events accumulate in a JS-local buffer.
 *   - Buffer is flushed every FLUSH_MS (default 4000) or when it
 *     exceeds FLUSH_MAX (default 25 events) or on visibilitychange
 *     to 'hidden'. Each flush calls Streamlit.setComponentValue with
 *     a monotonic seq number so Python can dedupe.
 * ========================================================= */

(function () {
  // The component config is templated in by Python; defaults below.
  var CFG = (window.__VITALS_ANALYTICS_CFG__ || {});
  var USER_ID    = CFG.user_id || null;
  var DEPT       = CFG.dept || null;
  var SESSION_ID = CFG.session_id || null;
  var PAGEVIEW_ID = CFG.pageview_id || null;
  var PAGE_PATH  = CFG.page_path || (location && location.pathname) || "/";
  var FLUSH_MS   = CFG.flush_ms || 4000;
  var FLUSH_MAX  = CFG.flush_max || 25;
  var STARTED_AT = Date.now();

  // Try to address the parent document (Streamlit page) — if we are
  // sandboxed cross-origin, we silently fall back to our own document.
  var hostDoc = document;
  var hostWin = window;
  try {
    if (window.parent && window.parent !== window && window.parent.document) {
      // touch a property to confirm same-origin access
      void window.parent.document.title;
      hostDoc = window.parent.document;
      hostWin = window.parent;
    }
  } catch (e) {
    // cross-origin — keep local document
  }

  var buffer = [];
  var errBuffer = [];
  var seq = 0;
  var maxScrollPct = 0;

  // Rage click tracking
  var lastClicks = []; // [{ts, key}]
  // Dead click detection — observe DOM mutations
  var lastClickAt = 0;
  var lastClickInteractiveTarget = false;
  var sawMutationSinceLastClick = false;

  function nowMs() { return Date.now(); }

  function elementKey(el) {
    if (!el || !el.tagName) return "";
    var k = el.tagName.toLowerCase();
    if (el.id) k += "#" + el.id;
    if (el.className && typeof el.className === "string") {
      // first class only, keeps key short
      var c = el.className.trim().split(/\s+/)[0];
      if (c) k += "." + c;
    }
    return k.slice(0, 200);
  }

  function elementLabel(el) {
    if (!el) return "";
    var t = (el.innerText || el.textContent || "").trim();
    if (!t) {
      t = el.getAttribute && (el.getAttribute("aria-label")
        || el.getAttribute("title")
        || el.getAttribute("alt")
        || el.getAttribute("placeholder")) || "";
    }
    return (t || "").slice(0, 500);
  }

  function isInteractive(el) {
    if (!el || !el.tagName) return false;
    var tag = el.tagName.toLowerCase();
    if (["a", "button", "input", "select", "textarea", "label", "summary"].indexOf(tag) >= 0) return true;
    if (el.getAttribute && el.getAttribute("role")) {
      var r = el.getAttribute("role");
      if (["button", "link", "checkbox", "tab", "menuitem", "switch"].indexOf(r) >= 0) return true;
    }
    if (el.onclick) return true;
    return false;
  }

  function pushEvent(ev) {
    ev.user_id     = USER_ID;
    ev.session_id  = SESSION_ID;
    ev.pageview_id = PAGEVIEW_ID;
    ev.page_path   = PAGE_PATH;
    ev.viewport_w  = hostWin.innerWidth;
    ev.viewport_h  = hostWin.innerHeight;
    buffer.push(ev);
    if (buffer.length >= FLUSH_MAX) flush();
  }

  function pushError(err) {
    err.user_id     = USER_ID;
    err.session_id  = SESSION_ID;
    err.pageview_id = PAGEVIEW_ID;
    err.page_path   = PAGE_PATH;
    err.user_agent  = navigator.userAgent;
    errBuffer.push(err);
  }

  function flush() {
    if (!buffer.length && !errBuffer.length && maxScrollPct === 0) return;
    seq += 1;
    var payload = {
      seq: seq,
      ts: nowMs(),
      pageview_id: PAGEVIEW_ID,
      events: buffer.splice(0, buffer.length),
      errors: errBuffer.splice(0, errBuffer.length),
      max_scroll_pct: maxScrollPct,
      duration_sec: Math.round((nowMs() - STARTED_AT) / 1000),
    };
    try {
      if (window.Streamlit && typeof window.Streamlit.setComponentValue === "function") {
        window.Streamlit.setComponentValue(payload);
      }
    } catch (e) {
      // Swallow — analytics MUST never break the app.
    }
  }

  // ---------- click ----------
  function onClick(e) {
    var target = e.target;
    if (!target) return;
    var x = (e.pageX != null) ? e.pageX : (e.clientX || 0);
    var y = (e.pageY != null) ? e.pageY : (e.clientY || 0);

    pushEvent({
      event_type: "click",
      element_id: elementKey(target),
      element_label: elementLabel(target),
      position_x: x,
      position_y: y,
    });

    // Rage click detection (3 clicks on same key within 500ms)
    var key = elementKey(target);
    var t = nowMs();
    lastClicks = lastClicks.filter(function (c) { return t - c.ts < 500; });
    lastClicks.push({ ts: t, key: key });
    var sameKey = lastClicks.filter(function (c) { return c.key === key; });
    if (sameKey.length >= 3) {
      pushEvent({
        event_type: "rage_click",
        element_id: key,
        element_label: elementLabel(target),
        position_x: x,
        position_y: y,
      });
      lastClicks = []; // reset to avoid spam
    }

    // Dead click detection setup
    lastClickAt = t;
    lastClickInteractiveTarget = isInteractive(target);
    sawMutationSinceLastClick = false;
    setTimeout(function () {
      if (lastClickAt && (nowMs() - lastClickAt) >= 240
          && !lastClickInteractiveTarget && !sawMutationSinceLastClick) {
        pushEvent({
          event_type: "dead_click",
          element_id: key,
          element_label: elementLabel(target),
          position_x: x,
          position_y: y,
        });
      }
    }, 260);
  }

  // ---------- submit ----------
  function onSubmit(e) {
    var f = e.target;
    pushEvent({
      event_type: "submit",
      element_id: elementKey(f),
      element_label: (f && f.name) || "",
    });
  }

  // ---------- scroll depth ----------
  function onScroll() {
    try {
      var doc = hostDoc.documentElement;
      var sTop = hostWin.pageYOffset || doc.scrollTop || 0;
      var vH = hostWin.innerHeight || doc.clientHeight || 1;
      var sH = doc.scrollHeight || 1;
      var pct = Math.min(100, Math.round(((sTop + vH) / sH) * 100));
      if (pct > maxScrollPct) maxScrollPct = pct;
    } catch (e) {}
  }

  // ---------- errors ----------
  function onError(e) {
    pushError({
      message: (e && (e.message || (e.error && e.error.message))) || "Unknown error",
      stack: (e && e.error && e.error.stack) || "",
      source: (e && e.filename) || "",
      line_no: (e && e.lineno) || null,
      col_no: (e && e.colno) || null,
    });
    flush();
  }

  function onRejection(e) {
    var r = e && e.reason;
    pushError({
      message: (r && (r.message || String(r))) || "UnhandledRejection",
      stack: (r && r.stack) || "",
      source: location.href,
      line_no: null,
      col_no: null,
    });
    flush();
  }

  // ---------- unload — final flush ----------
  function onHide() {
    onScroll(); // ensure latest depth
    if (maxScrollPct > 0) {
      pushEvent({
        event_type: "scroll",
        scroll_depth_pct: maxScrollPct,
        position_x: 0, position_y: 0,
      });
    }
    flush();
  }

  // ---------- DOM mutation observer (for dead-click detection) ----------
  try {
    if (hostDoc && hostDoc.body && typeof MutationObserver !== "undefined") {
      var mo = new MutationObserver(function () {
        if (lastClickAt && (nowMs() - lastClickAt) < 1000) {
          sawMutationSinceLastClick = true;
        }
      });
      mo.observe(hostDoc.body, { childList: true, subtree: true, attributes: true, characterData: false });
    }
  } catch (e) {}

  // ---------- attach ----------
  try {
    hostDoc.addEventListener("click", onClick, true);
    hostDoc.addEventListener("submit", onSubmit, true);
    hostWin.addEventListener("scroll", onScroll, { passive: true });
    hostWin.addEventListener("error", onError, true);
    hostWin.addEventListener("unhandledrejection", onRejection, true);
    hostDoc.addEventListener("visibilitychange", function () {
      if (hostDoc.visibilityState === "hidden") onHide();
    });
    hostWin.addEventListener("pagehide", onHide);
    hostWin.addEventListener("beforeunload", onHide);
  } catch (e) {}

  // Periodic flush
  setInterval(flush, FLUSH_MS);

  // Allow the host shell (index.html) to push updated CFG on each
  // Streamlit rerun (pageview_id can change when navigating pages).
  window.__vitalsUpdateCfg__ = function (next) {
    if (!next) return;
    if (next.user_id    != null) USER_ID    = next.user_id;
    if (next.dept       != null) DEPT       = next.dept;
    if (next.session_id != null) SESSION_ID = next.session_id;
    if (next.pageview_id!= null) PAGEVIEW_ID = next.pageview_id;
    if (next.page_path  != null) PAGE_PATH  = next.page_path;
  };
})();
