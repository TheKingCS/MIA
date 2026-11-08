/*
 * spatial.js — MIA's spatial components (DEC-0130, claude, 2026-11-08).
 *   MIASpatial.vapor(canvas, hues)  smoky RGB light drifting on black: a few big soft lights in the areas' hues,
 *                                   drawn small and blurred by CSS (cheap), paused when hidden, still under reduced
 *                                   motion. Returns a stop function.
 *   MIASpatial.ring(box, items, opt) the portals on a turning ring: the one in front large, the rest receding to each
 *                                   side; turn with the arrows, swipe, the wheel or a click on a side portal; Enter or
 *                                   a click on the front one goes through. Links stay real links in sidebar order.
 *   MIASpatial.enter(el, href, hue)  going through: the portal comes toward you, its light fills the room, then the
 *                                   page changes (at once under reduced motion).
 * What the portals are and what needs you comes from core (core/web_nexus.py); this only moves light around.
 */
(function () {
  "use strict";
  const still = () => window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;

  function vapor(canvas, hues) {
    const ctx = canvas.getContext("2d");
    const W = 160, H = 100;  // drawn tiny, blurred big by CSS
    canvas.width = W; canvas.height = H;
    const lights = (hues.length ? hues : ["#35d4ff"]).slice(0, 7).map((hue, i) => ({
      hue, x: Math.random() * W, y: H * (0.3 + Math.random() * 0.7), r: 30 + Math.random() * 40,
      dx: (Math.random() - 0.5) * 0.12, dy: (Math.random() - 0.5) * 0.06, phase: i * 1.7 }));
    let raf = 0, t = 0;
    function frame() {
      t += 1;
      ctx.globalCompositeOperation = "source-over";
      ctx.fillStyle = "rgba(0,0,0,0.22)";  // the old light fades: smoke, not paint
      ctx.fillRect(0, 0, W, H);
      ctx.globalCompositeOperation = "lighter";
      for (const l of lights) {
        l.x += l.dx + Math.sin((t + l.phase * 60) / 240) * 0.08;
        l.y += l.dy + Math.cos((t + l.phase * 40) / 300) * 0.05;
        if (l.x < -l.r) l.x = W + l.r; if (l.x > W + l.r) l.x = -l.r;
        if (l.y < H * 0.15) l.dy = Math.abs(l.dy); if (l.y > H) l.dy = -Math.abs(l.dy);
        const pulse = 0.1 + 0.06 * Math.sin((t + l.phase * 50) / 90);  // faint: smoke catching light, never a wash
        const g = ctx.createRadialGradient(l.x, l.y, 0, l.x, l.y, l.r);
        g.addColorStop(0, hex(l.hue, pulse));
        g.addColorStop(1, hex(l.hue, 0));
        ctx.fillStyle = g;
        ctx.beginPath(); ctx.arc(l.x, l.y, l.r, 0, Math.PI * 2); ctx.fill();
      }
      raf = 0;
      if (!still() && document.visibilityState === "visible") raf = requestAnimationFrame(frame);
    }
    for (let i = 0; i < 40; i++) frame();  // start with the room already filled
    const wake = () => { if (!raf && !still() && document.visibilityState === "visible") raf = requestAnimationFrame(frame); };
    document.addEventListener("visibilitychange", wake);
    wake();
    return () => { cancelAnimationFrame(raf); document.removeEventListener("visibilitychange", wake); };
  }

  function hex(color, alpha) {
    const n = parseInt(color.slice(1), 16);
    return "rgba(" + (n >> 16 & 255) + "," + (n >> 8 & 255) + "," + (n & 255) + "," + alpha + ")";
  }

  function ring(box, items, opt) {
    opt = opt || {};
    let front = opt.start || 0;
    const n = items.length;
    const step = opt.step || 24;  // degrees between portals
    function place() {
      items.forEach((el, i) => {
        let d = i - front;
        if (d > n / 2) d -= n;
        if (d < -n / 2) d += n;
        const a = d * step, far = Math.abs(d);
        // The inside wall of a round chamber, you near its centre: each portal stands at its angle around you,
        // facing in, so the ones beside the front one curve toward you like the reference image.
        const r = opt.radius ? opt.radius() : 700;
        el.style.transform = "translateZ(" + r + "px) rotateY(" + a + "deg) translateZ(" + (-r) + "px)" + (far ? "" : " scale(1.06)");
        el.style.opacity = far > 3 ? "0" : String(1 - far * 0.2);
        el.style.filter = "";  // a filter on a 3D layer cuts its glow into a box; distance shows by opacity instead
        el.style.zIndex = String(100 - far);
        el.style.pointerEvents = far > 3 ? "none" : "";
        el.classList.toggle("front", d === 0);
        el.tabIndex = d === 0 ? 0 : -1;
        el.setAttribute("aria-current", d === 0 ? "true" : "false");
      });
      if (opt.onTurn) opt.onTurn(front);
    }
    function turn(by) { front = (front + by + n) % n; place(); }
    function go(i) { front = i; place(); }
    items.forEach((el, i) => el.addEventListener("click", (e) => {
      if (i !== front) { e.preventDefault(); go(i); return; }
      if (opt.onEnter) { e.preventDefault(); opt.onEnter(el, i); }
    }));
    box.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight") { e.preventDefault(); turn(1); items[front].focus(); }
      if (e.key === "ArrowLeft") { e.preventDefault(); turn(-1); items[front].focus(); }
    });
    let wheelAt = 0;
    box.addEventListener("wheel", (e) => {
      const now = Date.now();
      if (now - wheelAt < 280) return;
      const d = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
      if (Math.abs(d) < 8) return;
      wheelAt = now; e.preventDefault(); turn(d > 0 ? 1 : -1);
    }, { passive: false });
    let x0 = null;
    box.addEventListener("pointerdown", (e) => { x0 = e.clientX; });
    box.addEventListener("pointerup", (e) => {
      if (x0 == null) return;
      const dx = e.clientX - x0; x0 = null;
      if (Math.abs(dx) > 40) turn(dx < 0 ? 1 : -1);
    });
    place();
    return { turn, go, get front() { return front; } };
  }

  function enter(el, href, hue) {
    if (still()) { location.href = href; return; }
    const flash = document.createElement("div");
    flash.className = "nexus-flash";
    flash.style.setProperty("--hue", hue || "#35d4ff");
    document.body.append(flash);
    el.classList.add("entering");
    el.style.transform += " translateZ(420px) scale(1.6)";
    el.style.opacity = "0";
    requestAnimationFrame(() => flash.classList.add("on"));
    setTimeout(() => { location.href = href; }, 480);
  }

  window.MIASpatial = { vapor, ring, enter };
})();
