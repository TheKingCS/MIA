/*
 * nexus3d.js — the Nexus as a room you stand in (DEC-0130, claude, 2026-11-08; Zac: "spatial, like you're in a room",
 * "almost game like and animated, flowing, seamless", everything orbiting MIA).
 *
 * What it is: a real-time scene drawn on the graphics card (WebGL 2, written here with no library, so MIA stays
 * offline and has nothing to download). MIA's orb stands on a glowing platform in the middle of a dark round chamber;
 * the areas' portals stand around her on a curved ring, each framed in its own colour with fire and smoke rising off
 * it; the floor is glossy and reflects them; motes of light drift up; bright light blooms. Turning the ring brings
 * a portal to the back-centre, behind her, where it's the one chosen; going through flies the camera into it.
 *
 * What it isn't: the facts. Which portals there are, their colours and what needs you come from core
 * (core/web_nexus.py through nexus.js); the labels and the info card are ordinary page text, so they stay sharp and
 * readable, and the portals stay real links for the keyboard and screen readers (MIASpatial.ring).
 *
 * How:
 *   MIANexus3D.supported()                   WebGL 2 is there and motion is allowed (else nexus.js keeps the CSS ring)
 *   MIANexus3D.mount(canvas, portals, opt)   draws the room; returns {focus(i), enter(i, href), orbAt(), stop()}
 *     opt.onPick(i)   a portal was clicked (nexus.js turns to it, or goes through when it's the chosen one)
 *     opt.onOrb()     the orb was clicked
 *     opt.onDrag(d)   the ring was dragged d portals (fractional while dragging); opt.onDrop(i) where it settled
 *     opt.labels      a box for the portals' name labels (page text, placed over the scene each frame)
 *     opt.shape       "oval" (portals, the default) or "bay" (an area's room: a wide door frame, as the Garage's bays)
 *     opt.fire        how much fire rises off the frames (1 the default; an area's room burns lower)
 *     opt.theme       the theme's room light (core/themes.py: accent, back_top/back_bottom, palette, fire, bloom,
 *                     mist, scan, grain); Stark's when absent
 *     opt.art(p)      a promise of the picture's url (default p.art); opt.needsGlow: a pedestal glows amber when
 *                     something in its item needs you; opt.arrive / opt.arriveHue: you came in through a portal
 *   The same room draws an area's own space (hub.js: the Garage's bays round her), so going through feels like one place.
 *   Portal art: each portal's `art` (web/img/portals/<area id>.jpg, Muse, H-0096); until one is there, a placeholder
 *   in its colour with its icon.
 * Each frame: background → the floor's reflection → the floor → motes → portals behind her → her beam and orb →
 * portals in front → low mist, into a half-float buffer; then bloom (bright pass, two blur sizes) and a tone map.
 */
(function () {
  "use strict";

  const reduced = () => window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;

  function supported() {
    if (reduced()) return false;
    try { return !!document.createElement("canvas").getContext("webgl2"); } catch (e) { return false; }
  }

  // ------------------------------------------------------------------ small matrix maths (column-major, like GL)
  function perspective(fovy, aspect, near, far) {
    const f = 1 / Math.tan(fovy / 2), nf = 1 / (near - far);
    return [f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) * nf, -1, 0, 0, 2 * far * near * nf, 0];
  }
  function lookAt(e, t, u) {
    let zx = e[0] - t[0], zy = e[1] - t[1], zz = e[2] - t[2];
    let l = Math.hypot(zx, zy, zz); zx /= l; zy /= l; zz /= l;
    let xx = u[1] * zz - u[2] * zy, xy = u[2] * zx - u[0] * zz, xz = u[0] * zy - u[1] * zx;
    l = Math.hypot(xx, xy, xz); xx /= l; xy /= l; xz /= l;
    const yx = zy * xz - zz * xy, yy = zz * xx - zx * xz, yz = zx * xy - zy * xx;
    return [xx, yx, zx, 0, xy, yy, zy, 0, xz, yz, zz, 0,
      -(xx * e[0] + xy * e[1] + xz * e[2]), -(yx * e[0] + yy * e[1] + yz * e[2]), -(zx * e[0] + zy * e[1] + zz * e[2]), 1];
  }
  function mul(a, b) {
    const o = new Array(16);
    for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) {
      o[c * 4 + r] = a[r] * b[c * 4] + a[4 + r] * b[c * 4 + 1] + a[8 + r] * b[c * 4 + 2] + a[12 + r] * b[c * 4 + 3];
    }
    return o;
  }
  function project(m, p, w, h) {  // world point -> [x, y, depth, visible] in CSS pixels
    const x = m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12];
    const y = m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13];
    const q = m[3] * p[0] + m[7] * p[1] + m[11] * p[2] + m[15];
    if (q <= 0.01) return [0, 0, q, false];
    return [(x / q * 0.5 + 0.5) * w, (1 - (y / q * 0.5 + 0.5)) * h, q, true];
  }
  function rgb(hex) {
    const n = parseInt(String(hex || "#35d4ff").slice(1), 16);
    return [(n >> 16 & 255) / 255, (n >> 8 & 255) / 255, (n & 255) / 255];
  }
  const mix3 = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];

  // ------------------------------------------------------------------ shaders
  const NOISE = `
    float hash(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
    float noise(vec2 p){ vec2 i = floor(p), f = fract(p); vec2 u = f * f * (3.0 - 2.0 * f);
      return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y); }
    float fbm(vec2 p){ float v = 0.0, a = 0.5; for (int i = 0; i < 5; i++){ v += a * noise(p); p = p * 2.03 + vec2(1.7, 9.2); a *= 0.5; } return v; }
  `;
  const HEAD = "#version 300 es\nprecision highp float;\n";

  // A quad standing upright, facing the camera across the floor (portals, orb, beam); mirrored for the reflection.
  const VS_BILL = HEAD + `
    in vec2 aPos; uniform mat4 uVP; uniform vec3 uBase; uniform vec3 uRight; uniform vec2 uHalf; uniform float uMirror;
    out vec2 vP;
    void main(){ vP = aPos * uHalf; vec3 w = uBase + uRight * vP.x + vec3(0.0, uHalf.y + vP.y, 0.0); w.y *= uMirror;
      gl_Position = uVP * vec4(w, 1.0); }`;

  // A portal: the art in an oval, the frame's line, and fire and smoke rising off it. Premultiplied: the art covers
  // what's behind it, the light adds.
  const FS_PORTAL = HEAD + NOISE + `
    in vec2 vP; out vec4 o;
    uniform sampler2D uArt; uniform vec3 uHue, uHue2; uniform vec2 uHalf;
    uniform float uT, uFocus, uVis, uSeed, uGain, uMirror, uShape, uFire;
    void main(){
      // the frame: an oval (a portal) or a wide rounded door (a garage bay)
      vec2 ab = uShape < 0.5 ? vec2(0.66, 1.0) : vec2(1.15, 0.8);
      vec2 q = vP - vec2(0.0, uShape < 0.5 ? -0.18 : -0.12);
      float e, d;
      if (uShape < 0.5){ e = length(q / ab); d = (e - 1.0) * 0.66; }
      else { vec2 k = abs(q) - ab + 0.14; d = length(max(k, 0.0)) + min(max(k.x, k.y), 0.0) - 0.14;
             e = max(abs(q.x) / ab.x, abs(q.y) / ab.y); }
      vec3 col = vec3(0.0); float a = 0.0;
      if (d < 0.0){
        vec2 uv = q / ab * 0.5 + 0.5;
        float sw = 0.010 * sin(uT * 0.7 + uv.y * 6.0 + uSeed);
        vec3 art = texture(uArt, vec2(uv.x + sw, 1.0 - uv.y)).rgb;
        col = art * mix(0.18, 1.0, smoothstep(1.0, 0.5, e)) * (0.45 + 0.55 * uFocus);
        col += uHue * pow(e, 7.0) * 0.7;
        a = 1.0;
      }
      float rim = exp(-abs(d) * 42.0), halo = exp(-abs(d) * 7.0);
      col += (uHue * 1.3 + vec3(0.25) * rim) * rim * (0.8 + 1.0 * uFocus) + uHue * halo * (0.18 + 0.2 * uFocus);
      if (d > -0.08){
        vec2 sp = vec2(vP.x * 1.9 + uSeed, vP.y * 1.25 - uT * 0.6);
        vec2 warp = vec2(fbm(sp + vec2(0.0, uT * 0.25)), fbm(sp + vec2(5.2, 1.3) - uT * 0.12));
        float n = fbm(sp * 1.5 + warp * 1.8);
        float out_ = max(d, 0.0);
        float reach = 0.42 + 0.42 * smoothstep(-0.8, 1.4, vP.y);
        float m = smoothstep(reach, 0.0, out_) * smoothstep(0.30, 0.78, n);
        vec3 fire = mix(uHue2, uHue, smoothstep(0.0, 0.45, out_ + (n - 0.5) * 0.3));
        col += (fire * pow(m, 1.5) * (0.75 + 0.75 * uFocus) + vec3(1.0) * pow(m, 6.0) * 0.12) * uFire;
      }
      float edge = smoothstep(1.0, 0.82, abs(vP.x) / uHalf.x) * smoothstep(1.0, 0.86, abs(vP.y) / uHalf.y);
      float fade = uMirror < 0.0 ? smoothstep(1.0, -1.0, vP.y / uHalf.y) : 1.0;
      float k = uVis * uGain * fade;
      o = vec4(col * edge * k, a * k);
    }`;

  // MIA's orb: a glass sphere with light swirling inside, a rim, and three tilted orbits with sparks running them.
  const FS_ORB = HEAD + NOISE + `
    in vec2 vP; out vec4 o; uniform float uT, uGain, uPulse; uniform vec3 uHue;
    void main(){
      vec2 p = vP / 0.62;
      float r = length(p);
      vec3 col = vec3(0.0); float a = 0.0;
      if (r < 1.0){
        float z = sqrt(1.0 - r * r);
        vec3 n = vec3(p, z);
        vec2 s = vec2(atan(n.x, n.z) * 1.2 + uT * 0.12, n.y * 2.0);
        float sw = fbm(s * 2.5 + fbm(s * 3.0 - uT * 0.1) * 2.0);
        vec3 base = mix(vec3(0.0, 0.03, 0.08), uHue * 0.9, smoothstep(0.38, 0.85, sw));
        col = base * (0.5 + 0.6 * z) + uHue * pow(1.0 - z, 2.5) * 1.8 + vec3(0.8, 0.95, 1.0) * pow(z, 8.0) * 0.4;
        col += uHue * exp(-abs(fract(n.y * 5.0 + uT * 0.04) - 0.5) * 34.0) * 0.18;
        col *= 1.0 + 0.25 * uPulse;
        a = 1.0;
      } else {
        col += uHue * exp(-(r - 1.0) * 4.5) * (0.5 + 0.3 * uPulse);
      }
      for (int i = 0; i < 3; i++){
        float fi = float(i);
        float ang = 0.32 + fi * 1.05 + uT * 0.04 * (fi + 1.0);
        mat2 R = mat2(cos(ang), -sin(ang), sin(ang), cos(ang));
        vec2 rp = R * p;
        vec2 q = vec2(rp.x, rp.y / (0.2 + 0.07 * fi));
        float ring = abs(length(q) - 1.5 - 0.12 * fi);
        float sa = atan(q.y, q.x);
        float spark = pow(max(0.0, cos(sa - uT * (0.7 + 0.35 * fi))), 60.0);
        float behind = (rp.y > 0.0 && r < 1.0) ? 0.0 : 1.0;
        col += uHue * exp(-ring * 16.0) * (0.45 + 5.0 * spark) * behind;
      }
      o = vec4(col * uGain, a * uGain);
    }`;

  // The column of light from the platform up to her.
  const FS_BEAM = HEAD + `
    in vec2 vP; out vec4 o; uniform vec2 uHalf; uniform float uT, uGain; uniform vec3 uHue;
    void main(){
      float y = vP.y / uHalf.y * 0.5 + 0.5;
      float core = exp(-abs(vP.x) * 30.0), wide = exp(-abs(vP.x) * 6.0);
      float flick = 0.8 + 0.2 * sin(uT * 3.0 + y * 20.0);
      vec3 col = (uHue * 1.4 * core + uHue * 0.25 * wide) * flick * smoothstep(1.0, 0.2, y);
      o = vec4(col * uGain, 0.0);
    }`;

  // The floor: glossy dark panels, the turning rings of her platform, and each portal's pedestal in its colour.
  const VS_FLOOR = HEAD + `
    in vec2 aPos; uniform mat4 uVP; out vec2 vW;
    void main(){ vW = vec2(aPos.x * 32.0, aPos.y * 32.0 - 4.0); gl_Position = uVP * vec4(vW.x, 0.0, vW.y, 1.0); }`;
  const FS_FLOOR = HEAD + `
    in vec2 vW; out vec4 o; uniform float uT; uniform vec3 uAccent; uniform vec4 uPed[16]; uniform vec3 uPedHue[16];
    uniform int uN; uniform vec2 uOrb;
    void main(){
      vec2 p = vW; float r = length(p);
      vec3 col = vec3(0.003, 0.008, 0.015);
      vec2 g = abs(fract(p * 0.5) - 0.5);
      col += uAccent * exp(-min(g.x, g.y) * 70.0) * 0.06 * exp(-r * 0.1);
      col += uAccent * exp(-abs(fract(r * 0.4) - 0.5) * 50.0) * 0.05 * exp(-r * 0.08);
      vec2 po = p - uOrb; float ro = length(po), ang = atan(po.y, po.x);
      for (int i = 0; i < 4; i++){
        float fi = float(i);
        float band = exp(-abs(ro - (0.8 + fi * 0.5)) * (46.0 - fi * 7.0));
        float dir = mod(fi, 2.0) * 2.0 - 1.0;
        float dash = 0.5 + 0.5 * step(0.35, fract(ang / 6.2832 * (10.0 + fi * 8.0) + uT * (0.03 + 0.015 * fi) * dir));
        col += uAccent * band * dash * (1.6 - fi * 0.3);
      }
      col += uAccent * exp(-ro * 1.8) * 0.45;
      for (int i = 0; i < 16; i++){
        if (i >= uN) break;
        vec4 pd = uPed[i];
        float d = length(p - pd.xy);
        float ring = exp(-abs(d - 0.8) * 34.0) * 0.9 + exp(-abs(d - 0.5) * 50.0) * 0.5 + exp(-d * 2.4) * 0.22;
        col += uPedHue[i] * ring * pd.z * (0.55 + 0.9 * pd.w);
      }
      col *= exp(-max(r - 7.0, 0.0) * 0.16);
      o = vec4(col, 0.74);
    }`;

  // Full-screen passes share one vertex shader.
  const VS_FULL = HEAD + `in vec2 aPos; out vec2 vUv; void main(){ vUv = aPos * 0.5 + 0.5; gl_Position = vec4(aPos, 0.0, 1.0); }`;

  // The chamber behind: dark, its wall's seams lit faintly, and vapor drifting in the areas' colours.
  const FS_BACK = HEAD + NOISE + `
    in vec2 vUv; out vec4 o; uniform float uT, uYaw; uniform vec3 uHues[6]; uniform vec3 uAccent, uTop, uBottom;
    void main(){
      vec2 uv = vUv;
      vec3 col = mix(uBottom, uTop, smoothstep(0.1, 0.75, uv.y));
      float x = uv.x * 16.0 + uYaw * 2.5;
      float seam = exp(-abs(fract(x) - 0.5) * 50.0) * smoothstep(0.38, 0.6, uv.y) * smoothstep(1.0, 0.7, uv.y);
      col += uAccent * seam * 0.06;
      col += uAccent * exp(-abs(uv.y - 0.86) * 160.0) * 0.12 * (0.6 + 0.4 * sin(uv.x * 30.0 + uT));
      col += uAccent * exp(-abs(uv.y - 0.62) * 220.0) * 0.06;
      for (int i = 0; i < 6; i++){
        float fi = float(i);
        vec2 c = vec2(0.08 + fi * 0.17 + 0.05 * sin(uT * 0.05 + fi + uYaw * 0.3), 0.5 + 0.16 * sin(fi * 1.7 + uT * 0.06));
        float n = fbm(uv * vec2(3.0, 2.2) + vec2(fi * 3.1, -uT * 0.04));
        float d = length((uv - c) * vec2(1.5, 1.0));
        col += uHues[i] * smoothstep(0.42, 0.0, d) * n * 0.22;
      }
      o = vec4(col, 1.0);
    }`;

  // Low mist rolling across the front of the room.
  const FS_MIST = HEAD + NOISE + `
    in vec2 vUv; out vec4 o; uniform float uT, uGain; uniform vec3 uHue, uAccent;
    void main(){
      float n = fbm(vUv * vec2(4.0, 3.0) + vec2(uT * 0.03, -uT * 0.015));
      float n2 = fbm(vUv * vec2(7.0, 4.0) - vec2(uT * 0.05, 0.0));
      float low = smoothstep(0.42, 0.0, vUv.y);
      vec3 col = mix(uAccent, uHue, 0.5 + 0.5 * sin(vUv.x * 3.0 + uT * 0.1)) * pow(n * n2 * 2.2, 2.0) * low * 0.35 * uGain;
      o = vec4(col, 0.0);
    }`;

  // Motes of light rising round the room.
  const VS_MOTE = HEAD + `
    in vec3 aSeed; uniform mat4 uVP; uniform float uT, uScale; out float vA;
    void main(){
      float y = mod(aSeed.y * 6.0 + uT * (0.06 + aSeed.z * 0.12), 6.0);
      float ang = aSeed.x * 6.2832 + uT * 0.015 * (aSeed.z - 0.5);
      float r = 1.2 + aSeed.z * 8.0;
      vec3 w = vec3(sin(ang) * r, y, -cos(ang) * r);
      gl_Position = uVP * vec4(w, 1.0);
      gl_PointSize = (1.5 + aSeed.z * 3.0) * uScale / gl_Position.w;
      vA = smoothstep(0.0, 0.6, y) * smoothstep(6.0, 4.0, y) * (0.25 + 0.75 * aSeed.y);
    }`;
  const FS_MOTE = HEAD + `
    in float vA; out vec4 o; uniform vec3 uAccent;
    void main(){ vec2 c = gl_PointCoord - 0.5; float g = exp(-dot(c, c) * 16.0); o = vec4(uAccent * g * vA * 1.3, 0.0); }`;

  // Bloom: keep what's bright, blur it at two sizes, add it back, tone map, darken the corners.
  const FS_BRIGHT = HEAD + `in vec2 vUv; out vec4 o; uniform sampler2D uSrc;
    void main(){ vec3 c = texture(uSrc, vUv).rgb; float l = max(c.r, max(c.g, c.b));
      o = vec4(c * smoothstep(0.8, 1.6, l), 1.0); }`;
  const FS_BLUR = HEAD + `in vec2 vUv; out vec4 o; uniform sampler2D uSrc; uniform vec2 uDir;
    void main(){ vec3 c = texture(uSrc, vUv).rgb * 0.227;
      c += (texture(uSrc, vUv + uDir * 1.385).rgb + texture(uSrc, vUv - uDir * 1.385).rgb) * 0.316;
      c += (texture(uSrc, vUv + uDir * 3.231).rgb + texture(uSrc, vUv - uDir * 3.231).rgb) * 0.070;
      o = vec4(c, 1.0); }`;
  const FS_FINAL = HEAD + NOISE + `in vec2 vUv; out vec4 o; uniform sampler2D uScene, uB1, uB2; uniform float uT, uFlash, uBloom, uScan, uGrain; uniform vec3 uFlashHue;
    vec3 aces(vec3 x){ return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0); }
    void main(){
      vec3 c = texture(uScene, vUv).rgb + (texture(uB1, vUv).rgb * 0.55 + texture(uB2, vUv).rgb * 0.8) * uBloom;
      c = aces(c * 0.95);
      vec2 v = vUv - 0.5; c *= 1.0 - dot(v, v) * 0.9;
      c *= 1.0 - uScan * 0.22 * step(0.5, fract(gl_FragCoord.y * 0.5));  // a theme's scanlines
      c += (hash(vUv * 900.0 + uT) - 0.5) * (0.018 + 0.06 * uGrain);
      c = mix(c, uFlashHue, uFlash);
      o = vec4(c, 1.0);
    }`;

  // ------------------------------------------------------------------ GL plumbing
  function program(gl, vs, fs) {
    const make = (type, src) => {
      const s = gl.createShader(type);
      gl.shaderSource(s, src); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
      return s;
    };
    const p = gl.createProgram();
    gl.attachShader(p, make(gl.VERTEX_SHADER, vs)); gl.attachShader(p, make(gl.FRAGMENT_SHADER, fs));
    gl.bindAttribLocation(p, 0, "aPos"); gl.bindAttribLocation(p, 1, "aSeed");
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
    const loc = {};
    const u = (name) => (name in loc ? loc[name] : (loc[name] = gl.getUniformLocation(p, name)));
    return { p, u };
  }

  // Art is fitted to the frame's shape (cover, centred) before it goes to the card: an oval portal is 2:3, a bay 3:2.
  const ART = { oval: [384, 576], bay: [576, 384] };
  function cover(img, shape) {
    const [w, h] = ART[shape] || ART.oval;
    const c = document.createElement("canvas");
    c.width = w; c.height = h;
    const k = Math.max(w / img.width, h / img.height);
    c.getContext("2d").drawImage(img, (w - img.width * k) / 2, (h - img.height * k) / 2, img.width * k, img.height * k);
    return c;
  }

  function placeholder(portal, shape) {  // the art until a picture arrives: its colour, deep, with its icon
    const [W0, H0] = ART[shape] || ART.oval;
    const c = document.createElement("canvas");
    c.width = W0; c.height = H0;
    const x = c.getContext("2d");
    const [r, g, b] = rgb(portal.hue).map((v) => Math.round(v * 255));
    const grad = x.createRadialGradient(W0 / 2, H0 * 0.57, 10, W0 / 2, H0 * 0.52, Math.max(W0, H0) * 0.6);
    grad.addColorStop(0, `rgba(${r},${g},${b},0.55)`);
    grad.addColorStop(0.45, `rgba(${r >> 2},${g >> 2},${b >> 2},0.9)`);
    grad.addColorStop(1, "#000");
    x.fillStyle = grad; x.fillRect(0, 0, W0, H0);
    for (let i = 0; i < 90; i++) {  // a little starfield of light so the glass isn't flat
      x.fillStyle = `rgba(${r},${g},${b},${Math.random() * 0.5})`;
      x.fillRect(Math.random() * W0, Math.random() * H0, 1.5, 1.5);
    }
    return c;
  }

  function drawIcon(canvas, portal, done) {
    const svg = window.MIAIcons && MIAIcons.svg(portal.icon || "mia");
    if (!svg) { done(); return; }
    svg.setAttribute("width", "200"); svg.setAttribute("height", "200");
    if (!svg.getAttribute("xmlns")) svg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    const text = new XMLSerializer().serializeToString(svg).replace(/currentColor/g, "#ffffff");
    const img = new Image();
    img.onload = () => {
      const x = canvas.getContext("2d");
      x.globalAlpha = 0.85; x.shadowColor = portal.hue; x.shadowBlur = 30;
      x.drawImage(img, canvas.width / 2 - 100, canvas.height * 0.55 - 100, 200, 200);
      done();
    };
    img.onerror = done;
    img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(text);
  }

  function mount(canvas, portals, opt) {
    opt = opt || {};
    const gl = canvas.getContext("webgl2", { antialias: false, alpha: false, premultipliedAlpha: false, powerPreference: "high-performance" });
    if (!gl) return null;
    const floatOk = !!gl.getExtension("EXT_color_buffer_float");
    gl.getExtension("OES_texture_float_linear");

    let P;
    try {
      P = {
        portal: program(gl, VS_BILL, FS_PORTAL), orb: program(gl, VS_BILL, FS_ORB), beam: program(gl, VS_BILL, FS_BEAM),
        floor: program(gl, VS_FLOOR, FS_FLOOR), back: program(gl, VS_FULL, FS_BACK), mist: program(gl, VS_FULL, FS_MIST),
        mote: program(gl, VS_MOTE, FS_MOTE), bright: program(gl, VS_FULL, FS_BRIGHT), blur: program(gl, VS_FULL, FS_BLUR),
        final: program(gl, VS_FULL, FS_FINAL),
      };
    } catch (e) {
      console.warn("Nexus 3D: a shader didn't build, the flat Nexus shows instead", e);
      return null;
    }

    const quad = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, quad);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const quadVao = gl.createVertexArray();
    gl.bindVertexArray(quadVao); gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
    const MOTES = 260;
    const seeds = new Float32Array(MOTES * 3).map(() => Math.random());
    const moteVao = gl.createVertexArray();
    gl.bindVertexArray(moteVao);
    const mb = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, mb); gl.bufferData(gl.ARRAY_BUFFER, seeds, gl.STATIC_DRAW);
    gl.enableVertexAttribArray(1); gl.vertexAttribPointer(1, 3, gl.FLOAT, false, 0, 0);
    gl.bindVertexArray(null);

    // Each portal's art: the placeholder at once, its picture when it loads.
    const n = portals.length;
    const SHAPE = opt.shape === "bay" ? "bay" : "oval";
    const FIRE = (opt.fire == null ? 1 : opt.fire) * (opt.theme && typeof opt.theme.fire === "number" ? opt.theme.fire : 1);
    const AMBER = rgb("#f2b33d");
    const textures = portals.map((p) => {
      const t = gl.createTexture();
      const upload = (src) => {
        gl.bindTexture(gl.TEXTURE_2D, t);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, src);
        gl.generateMipmap(gl.TEXTURE_2D);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      };
      const ph = placeholder(p, SHAPE);
      upload(ph);
      drawIcon(ph, p, () => upload(ph));
      Promise.resolve(opt.art ? opt.art(p) : p.art).then((url) => {  // only pictures core says are there
        if (!url) return;
        const img = new Image();
        img.onload = () => upload(cover(img, SHAPE));
        img.src = url;
      }).catch(() => {});
      return t;
    });
    const hues = portals.map((p) => rgb(p.hue));
    const hue2 = hues.map((h, i) => mix3(h, hues[(i + 1) % n], 0.55));
    // The theme's light (DEC-0136, core/themes.py room): MIA's accent, the chamber's colours, a palette for the
    // vapor and mist, and how strong the fire, bloom, mist, scanlines and grain are. Portal frames keep their area's
    // hue whatever the theme (DEC-0130).
    const look = opt.theme || {};
    const accent = rgb(look.accent || "#35d4ff");
    const palette = (look.palette || []).map(rgb);
    const backTop = look.back_top ? rgb(look.back_top) : [0.008, 0.018, 0.035];
    const backBottom = look.back_bottom ? rgb(look.back_bottom) : [0, 0, 0.004];
    const level = (k, d) => (typeof look[k] === "number" ? look[k] : d);

    // Render targets: the scene at full size, bloom at half and a quarter.
    function target(w, h) {
      const tex = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texImage2D(gl.TEXTURE_2D, 0, floatOk ? gl.RGBA16F : gl.RGBA8, w, h, 0, gl.RGBA, floatOk ? gl.HALF_FLOAT : gl.UNSIGNED_BYTE, null);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      const fb = gl.createFramebuffer();
      gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
      return { tex, fb, w, h };
    }
    let T = null, W = 0, H = 0, cssW = 0, cssH = 0;
    function resize() {
      cssW = canvas.clientWidth || innerWidth; cssH = canvas.clientHeight || innerHeight;
      const dpr = Math.min(window.devicePixelRatio || 1, cssW < 700 ? 1.5 : 1.75);
      const w = Math.max(2, Math.round(cssW * dpr)), h = Math.max(2, Math.round(cssH * dpr));
      if (w === W && h === H && T) return;
      W = w; H = h; canvas.width = w; canvas.height = h;
      if (T) Object.values(T).forEach((t) => { gl.deleteTexture(t.tex); gl.deleteFramebuffer(t.fb); });
      const hw = Math.max(1, w >> 1), hh = Math.max(1, h >> 1), qw = Math.max(1, w >> 2), qh = Math.max(1, h >> 2);
      T = { scene: target(w, h), a1: target(hw, hh), b1: target(hw, hh), a2: target(qw, qh), b2: target(qw, qh) };
    }

    // Labels: page text over the scene.
    const labels = portals.map((p) => {
      if (!opt.labels) return null;
      const l = document.createElement("div");
      l.className = "n3-label";
      l.style.setProperty("--hue", p.hue);
      l.textContent = p.name;
      if (p.needs) {
        const b = document.createElement("b");
        b.textContent = String(p.needs);
        b.title = p.needs + (p.needs === 1 ? " needs you" : " need you");
        l.append(b);
      }
      opt.labels.append(l);
      return l;
    });

    // ------------------------------------------------------------ state
    const STEP = (Math.PI * 2) / Math.max(n, 7);  // radians between portals round the ring
    const R = 6.0, FOCUS_GROW = 0.3;  // the chosen portal stands a third taller
    let ORB = [0, 0.95, 2.0];  // her orb: low and forward, so the chosen portal stands clear behind her
    let rot = opt.start || 0, goal = rot, dragging = false;
    let pointer = [0, 0], drift = [0, 0];
    let flying = null;  // {i, href, t0}
    // Coming in through a portal: the light fades and the camera eases back out of it. Timed from the end of the first
    // frame, since the first one builds the shaders and can take a while.
    let arrive = 0;
    const arrived = () => (!opt.arrive ? 1 : arrive ? Math.min(1, (performance.now() - arrive) / 1400) : 0);
    let pulse = 0;
    let raf = 0, t0 = performance.now(), last = t0;
    const rects = new Array(n).fill(null);
    let orbRect = null, VP = null;

    const wrap = (d) => { d = ((d % n) + n) % n; return d > n / 2 ? d - n : d; };

    // Wide screens look across the room at her with the ring behind; a phone stands closer in, so the chosen portal
    // is big and its neighbours curve round you.
    function camera(t, aspect) {
      const portrait = aspect < 1;
      const fov = (portrait ? 60 : 44) * Math.PI / 180;
      ORB = portrait ? [0, 0.55, -2.2] : [0, 0.95, 2.0];
      let eye = portrait ? [0, 2.1, 5.4] : [0, 2.45, 10.8];
      eye = [eye[0] + Math.sin(t * 0.07) * 0.3 + drift[0] * 0.6, eye[1] + drift[1] * 0.25 + Math.sin(t * 0.11) * 0.06, eye[2]];
      let at = portrait ? [drift[0] * 0.2, 1.75, -6] : [drift[0] * 0.25, 1.65, -2.2];
      if (flying) {  // through the chosen portal
        const k = Math.max(0, Math.min(1, (performance.now() - flying.t0) / 750)), e = k * k * k;
        const tgt = [0, 1.55, -R + 0.2];
        eye = mix3(eye, tgt, e); at = mix3(at, [0, 1.55, -R - 3], e);
      } else if (arrived() < 1) {
        const e = 1 - Math.pow(1 - arrived(), 3);
        eye = mix3([0, 1.7, -R * 0.4], eye, e); at = mix3([0, 1.6, -R - 3], at, e);
      }
      return mul(perspective(fov, aspect, 0.1, 80), lookAt(eye, at, [0, 1, 0]));
    }

    function portalState(i) {
      const d = wrap(i - rot);
      const phi = d * STEP;
      // an oval ring, shallower than it is wide, so the far portals aren't lost in the distance
      const pos = [R * 1.1 * Math.sin(phi), 0.5, -R * 0.62 * Math.cos(phi) - 0.6];
      const vis = Math.max(0, Math.min(1, (1.8 - Math.abs(phi)) / 0.35));
      const focus = Math.max(0, 1 - Math.abs(d));
      return { pos, vis, focus, d };
    }

    function frame(now) {
      raf = 0;
      const dt = Math.min(0.05, (now - last) / 1000); last = now;
      const t = (now - t0) / 1000;
      resize();
      if (!dragging) rot += (goal - rot) * Math.min(1, dt * 5.5);
      drift[0] += (pointer[0] - drift[0]) * Math.min(1, dt * 2);
      drift[1] += (pointer[1] - drift[1]) * Math.min(1, dt * 2);
      pulse = Math.max(0, pulse - dt * 1.5);
      const aspect = cssW / cssH;
      VP = camera(t, aspect);
      // the camera's right, flattened on the floor, for facing the quads to it
      const right = [VP[0], 0, VP[8]];
      const rl = Math.hypot(right[0], right[2]) || 1; right[0] /= rl; right[2] /= rl;

      gl.bindFramebuffer(gl.FRAMEBUFFER, T.scene.fb);
      gl.viewport(0, 0, W, H);
      gl.disable(gl.DEPTH_TEST);
      gl.disable(gl.BLEND);
      gl.bindVertexArray(quadVao);

      // the chamber
      gl.useProgram(P.back.p);
      gl.uniform1f(P.back.u("uT"), t); gl.uniform1f(P.back.u("uYaw"), rot * STEP);
      const sixHues = [];
      for (let k = 0; k < 6; k++) sixHues.push(...(palette.length ? palette[k % palette.length] : hues[(Math.round(rot) + k * 3 + n * 4) % n]));
      gl.uniform3fv(P.back.u("uHues[0]"), sixHues); gl.uniform3fv(P.back.u("uAccent"), accent);
      gl.uniform3fv(P.back.u("uTop"), backTop); gl.uniform3fv(P.back.u("uBottom"), backBottom);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

      gl.enable(gl.BLEND);
      gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);

      const states = portals.map((_, i) => portalState(i));
      const order = states.map((s, i) => i).filter((i) => states[i].vis > 0.001)
        .sort((a, b) => states[a].pos[2] - states[b].pos[2]);  // far (more negative z) first

      const drawPortal = (i, mirror, gain) => {
        const s = states[i], sc = 1 + FOCUS_GROW * s.focus, half = SHAPE === "bay" ? [1.55 * sc, 1.25 * sc] : [1.2 * sc, 1.62 * sc];
        const u = P.portal.u;
        gl.uniform3f(u("uBase"), s.pos[0], s.pos[1], s.pos[2]);
        gl.uniform3fv(u("uRight"), right); gl.uniform2fv(u("uHalf"), half); gl.uniform1f(u("uMirror"), mirror);
        gl.uniform3fv(u("uHue"), hues[i]); gl.uniform3fv(u("uHue2"), hue2[i]);
        gl.uniform1f(u("uFocus"), s.focus); gl.uniform1f(u("uVis"), s.vis); gl.uniform1f(u("uSeed"), i * 7.31);
        gl.uniform1f(u("uGain"), gain); gl.uniform1f(u("uT"), t);
        gl.uniform1f(u("uShape"), SHAPE === "bay" ? 1 : 0); gl.uniform1f(u("uFire"), FIRE);
        gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, textures[i]); gl.uniform1i(u("uArt"), 0);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
        if (mirror > 0) rects[i] = rectOf([s.pos[0], s.pos[1], s.pos[2]], half, right, s);
      };
      const drawOrb = (mirror, gain) => {
        const u = P.orb.u, half = [1.15, 1.15];
        gl.useProgram(P.orb.p);
        gl.uniformMatrix4fv(u("uVP"), false, VP);
        gl.uniform3f(u("uBase"), ORB[0], ORB[1] - half[1], ORB[2]);
        gl.uniform3fv(u("uRight"), right); gl.uniform2fv(u("uHalf"), half); gl.uniform1f(u("uMirror"), mirror);
        gl.uniform1f(u("uT"), t); gl.uniform1f(u("uGain"), gain); gl.uniform1f(u("uPulse"), pulse);
        gl.uniform3fv(u("uHue"), accent);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      };
      const drawBeam = (gain) => {
        const u = P.beam.u, half = [0.35, (ORB[1] - 0.5) / 2];
        gl.useProgram(P.beam.p);
        gl.uniformMatrix4fv(u("uVP"), false, VP);
        gl.uniform3f(u("uBase"), ORB[0], 0, ORB[2]); gl.uniform3fv(u("uRight"), right); gl.uniform2fv(u("uHalf"), half);
        gl.uniform1f(u("uMirror"), 1); gl.uniform1f(u("uT"), t); gl.uniform1f(u("uGain"), gain); gl.uniform3fv(u("uHue"), accent);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      };

      // the floor's reflection, then the floor over it
      gl.useProgram(P.portal.p);
      gl.uniformMatrix4fv(P.portal.u("uVP"), false, VP);
      order.forEach((i) => drawPortal(i, -1, 0.45));
      drawOrb(-1, 0.4);

      gl.useProgram(P.floor.p);
      gl.uniformMatrix4fv(P.floor.u("uVP"), false, VP);
      gl.uniform1f(P.floor.u("uT"), t); gl.uniform3fv(P.floor.u("uAccent"), accent);
      const ped = [], pedHue = [];
      for (let i = 0; i < 16; i++) {
        const s = states[i];
        if (s) { ped.push(s.pos[0], s.pos[2], s.vis, s.focus); pedHue.push(...(opt.needsGlow && portals[i].needs ? AMBER : hues[i])); } else { ped.push(0, 0, 0, 0); pedHue.push(0, 0, 0); }
      }
      gl.uniform4fv(P.floor.u("uPed[0]"), ped); gl.uniform3fv(P.floor.u("uPedHue[0]"), pedHue);
      gl.uniform1i(P.floor.u("uN"), Math.min(16, n)); gl.uniform2f(P.floor.u("uOrb"), ORB[0], ORB[2]);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

      // motes
      gl.useProgram(P.mote.p);
      gl.uniformMatrix4fv(P.mote.u("uVP"), false, VP);
      gl.uniform1f(P.mote.u("uT"), t); gl.uniform1f(P.mote.u("uScale"), H / 90); gl.uniform3fv(P.mote.u("uAccent"), accent);
      gl.bindVertexArray(moteVao);
      gl.drawArrays(gl.POINTS, 0, MOTES);
      gl.bindVertexArray(quadVao);

      // portals behind her, her beam and orb, then the ones in front
      gl.useProgram(P.portal.p);
      order.filter((i) => states[i].pos[2] < ORB[2]).forEach((i) => drawPortal(i, 1, 1));
      drawBeam(1);
      drawOrb(1, 1);
      gl.useProgram(P.portal.p);
      gl.uniformMatrix4fv(P.portal.u("uVP"), false, VP);
      order.filter((i) => states[i].pos[2] >= ORB[2]).forEach((i) => drawPortal(i, 1, 1));
      portals.forEach((_, i) => { if (states[i].vis <= 0.001) rects[i] = null; });

      // mist
      gl.useProgram(P.mist.p);
      gl.uniform1f(P.mist.u("uT"), t); gl.uniform3fv(P.mist.u("uAccent"), accent);
      // the mist drifts from one palette colour to the next (t can be a hair below zero on the first frame)
      const pk = Math.max(0, t) / 6, pf = pk - Math.floor(pk), pi = Math.floor(pk);
      gl.uniform3fv(P.mist.u("uHue"), palette.length
        ? mix3(palette[pi % palette.length], palette[(pi + 1) % palette.length], pf)
        : hues[((Math.round(rot) % n) + n) % n]);
      gl.uniform1f(P.mist.u("uGain"), level("mist", 1));
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      gl.disable(gl.BLEND);

      // bloom
      const pass = (prog, dst, setup) => {
        gl.bindFramebuffer(gl.FRAMEBUFFER, dst ? dst.fb : null);
        gl.viewport(0, 0, dst ? dst.w : W, dst ? dst.h : H);
        gl.useProgram(prog.p); setup(prog.u); gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      };
      const tex = (unit, t2, u, name) => { gl.activeTexture(gl.TEXTURE0 + unit); gl.bindTexture(gl.TEXTURE_2D, t2.tex); gl.uniform1i(u(name), unit); };
      pass(P.bright, T.a1, (u) => tex(0, T.scene, u, "uSrc"));
      pass(P.blur, T.b1, (u) => { tex(0, T.a1, u, "uSrc"); gl.uniform2f(u("uDir"), 1.5 / T.a1.w, 0); });
      pass(P.blur, T.a1, (u) => { tex(0, T.b1, u, "uSrc"); gl.uniform2f(u("uDir"), 0, 1.5 / T.a1.h); });
      pass(P.blur, T.b2, (u) => { tex(0, T.a1, u, "uSrc"); gl.uniform2f(u("uDir"), 2.5 / T.b2.w, 0); });
      pass(P.blur, T.a2, (u) => { tex(0, T.b2, u, "uSrc"); gl.uniform2f(u("uDir"), 0, 2.5 / T.b2.h); });
      pass(P.final, null, (u) => {
        tex(0, T.scene, u, "uScene"); tex(1, T.a1, u, "uB1"); tex(2, T.a2, u, "uB2");
        gl.uniform1f(u("uT"), t);
        gl.uniform1f(u("uBloom"), level("bloom", 1)); gl.uniform1f(u("uScan"), level("scan", 0)); gl.uniform1f(u("uGrain"), level("grain", 0));
        const k = flying ? Math.max(0, Math.min(1, ((performance.now() - flying.t0) / 750 - 0.55) / 0.45))
          : Math.max(0, 1 - arrived() * 2);
        gl.uniform1f(u("uFlash"), k * 0.9); gl.uniform3fv(u("uFlashHue"), flying ? hues[flying.i] : opt.arriveHue ? rgb(opt.arriveHue) : accent);
      });

      // labels and the orb's spot for the page
      const o = project(VP, ORB, cssW, cssH), o2 = project(VP, [ORB[0], ORB[1] + 0.62, ORB[2]], cssW, cssH);
      orbRect = o[3] ? { x: o[0], y: o[1], r: Math.abs(o[1] - o2[1]) * 1.1 } : null;
      labels.forEach((l, i) => {
        if (!l) return;
        const s = states[i], sc = 1 + FOCUS_GROW * s.focus;
        const pt = project(VP, [s.pos[0], s.pos[1] + (SHAPE === "bay" ? 2.1 : 3.24) * sc + 0.12, s.pos[2]], cssW, cssH);
        const show = s.vis > 0.05 && pt[3] && (aspect >= 1 || Math.abs(s.d) < 1.5);
        l.style.opacity = show ? String(Math.min(1, s.vis) * (flying ? 0 : 1)) : "0";
        if (show) l.style.transform = "translate(" + pt[0].toFixed(1) + "px," + pt[1].toFixed(1) + "px) translate(-50%,-100%) scale(" + (0.85 + 0.25 * s.focus).toFixed(3) + ")";
        l.classList.toggle("on", s.focus > 0.5);
      });

      if (opt.arrive && !arrive) arrive = performance.now();
      if (flying && performance.now() - flying.t0 > 760) { location.href = flying.href; return; }
      if (document.visibilityState === "visible") raf = requestAnimationFrame(frame);
    }

    function rectOf(base, half, right, s) {
      const corners = [[-1, 0], [1, 0], [-1, 2], [1, 2]].map(([sx, sy]) =>
        project(VP, [base[0] + right[0] * half[0] * sx * 0.78, base[1] + half[1] * sy, base[2] + right[2] * half[0] * sx * 0.78], cssW, cssH));
      if (corners.some((c) => !c[3])) return null;
      const xs = corners.map((c) => c[0]), ys = corners.map((c) => c[1]);
      return { x0: Math.min(...xs), x1: Math.max(...xs), y0: Math.min(...ys), y1: Math.max(...ys), z: corners[0][2], s };
    }

    // ------------------------------------------------------------ input on the canvas
    let down = null;
    canvas.addEventListener("pointerdown", (e) => { down = { x: e.clientX, y: e.clientY, rot, moved: false }; canvas.setPointerCapture(e.pointerId); });
    canvas.addEventListener("pointermove", (e) => {
      const r = canvas.getBoundingClientRect();
      pointer = [((e.clientX - r.left) / r.width - 0.5) * 2, -((e.clientY - r.top) / r.height - 0.5) * 2];
      if (!down) return;
      const dx = e.clientX - down.x;
      if (Math.abs(dx) > 6) { down.moved = true; dragging = true; }
      if (dragging) { rot = down.rot - dx / Math.max(160, cssW / 7); if (opt.onDrag) opt.onDrag(rot); }
    });
    const release = (e) => {
      if (!down) return;
      const was = down; down = null;
      if (dragging) {
        dragging = false;
        goal = Math.round(rot);
        if (opt.onDrop) opt.onDrop(((goal % n) + n) % n);
        return;
      }
      if (was.moved || e.type === "pointercancel") return;
      const r = canvas.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
      if (orbRect && Math.hypot(x - orbRect.x, y - orbRect.y) < orbRect.r) { pulse = 1; if (opt.onOrb) opt.onOrb(); return; }
      const hit = rects.map((q, i) => ({ q, i })).filter(({ q }) => q && x >= q.x0 && x <= q.x1 && y >= q.y0 && y <= q.y1)
        .sort((a, b) => a.q.z - b.q.z)[0];
      if (hit && opt.onPick) opt.onPick(hit.i);
    };
    canvas.addEventListener("pointerup", release);
    canvas.addEventListener("pointercancel", release);
    canvas.addEventListener("pointerleave", () => { pointer = [0, 0]; });

    const wake = () => { if (!raf && document.visibilityState === "visible") { last = performance.now(); raf = requestAnimationFrame(frame); } };
    document.addEventListener("visibilitychange", wake);
    addEventListener("resize", wake);
    resize();
    wake();

    return {
      focus(i) { goal = i + n * Math.round((rot - i) / n); },      // the nearest way round
      enter(i, href) { this.focus(i); flying = { i, href, t0: performance.now() + 200 }; },
      orbAt() { return orbRect; },
      stop() {  // for a re-render: no more frames, and the graphics card's memory handed back
        cancelAnimationFrame(raf); raf = 0; flying = null;
        document.removeEventListener("visibilitychange", wake); removeEventListener("resize", wake);
        const lose = gl.getExtension("WEBGL_lose_context");
        if (lose) lose.loseContext();
        labels.forEach((l) => l && l.remove());
      },
    };
  }

  window.MIANexus3D = { supported, mount };
  window.MIARoom = window.MIANexus3D;  // the same engine for an area's own room
})();
