// One WebGL2 canvas behind the DOM cards. Draws each card's media band at the
// same projected quad as its CSS 3D transform, plus the centred card's aura
// (reflection above, glow below). Returns null when WebGL2 is unavailable.
import { BAND_VS, BAND_FS, QUAD_VS, BLUR_FS, AURA_VS, AURA_FS } from './shaders.js';

const hexToLin = h => {
  const n = parseInt(h.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255].map(v => Math.pow(v / 255, 2.2));
};
const hexToRgb = h => {
  const n = parseInt(h.slice(1), 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
};

function compile(gl, type, src) {
  const s = gl.createShader(type);
  gl.shaderSource(s, src);
  gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
  return s;
}
function program(gl, vs, fs) {
  const p = gl.createProgram();
  gl.attachShader(p, compile(gl, gl.VERTEX_SHADER, vs));
  gl.attachShader(p, compile(gl, gl.FRAGMENT_SHADER, fs));
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
  const u = {};
  const n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
  for (let i = 0; i < n; i++) {
    const info = gl.getActiveUniform(p, i);
    const name = info.name.replace(/\[0\]$/, '');
    u[name] = gl.getUniformLocation(p, info.name);
  }
  return { p, u };
}
function target(gl, w, h) {
  const tex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  const fb = gl.createFramebuffer();
  gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
  return { tex, fb, w, h };
}

export function createRenderer(canvas, palette) {
  const gl = canvas.getContext('webgl2', { alpha: false, antialias: false, premultipliedAlpha: true, powerPreference: 'high-performance' });
  if (!gl) return null;

  let band, blur, aura;
  try {
    band = program(gl, BAND_VS, BAND_FS);
    blur = program(gl, QUAD_VS, BLUR_FS);
    aura = program(gl, AURA_VS, AURA_FS);
  } catch (err) {
    console.error('[lab] shader build failed', err);
    return null;
  }

  // Band quad: 4 verts x (pos4 + uv2), rewritten per card.
  const bandVao = gl.createVertexArray();
  const bandBuf = gl.createBuffer();
  gl.bindVertexArray(bandVao);
  gl.bindBuffer(gl.ARRAY_BUFFER, bandBuf);
  gl.bufferData(gl.ARRAY_BUFFER, 4 * 6 * 4, gl.DYNAMIC_DRAW);
  gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 4, gl.FLOAT, false, 24, 0);
  gl.enableVertexAttribArray(1); gl.vertexAttribPointer(1, 2, gl.FLOAT, false, 24, 16);

  // Fullscreen quad for blur passes.
  const quadVao = gl.createVertexArray();
  gl.bindVertexArray(quadVao);
  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
  gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);

  // Aura quad in css px, rewritten per frame.
  const auraVao = gl.createVertexArray();
  const auraBuf = gl.createBuffer();
  gl.bindVertexArray(auraVao);
  gl.bindBuffer(gl.ARRAY_BUFFER, auraBuf);
  gl.bufferData(gl.ARRAY_BUFFER, 4 * 2 * 4, gl.DYNAMIC_DRAW);
  gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
  gl.bindVertexArray(null);

  // FBO chain for the aura: raw band -> light blur -> heavy blur.
  const raw = target(gl, 256, 192);
  const lightA = target(gl, 128, 96), lightB = target(gl, 128, 96);
  const heavyA = target(gl, 48, 36), heavyB = target(gl, 48, 36);

  const textures = new Map();
  const blank = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, blank);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([128, 128, 128, 255]));

  function loadTexture(url) {
    if (textures.has(url)) return textures.get(url);
    const rec = { tex: blank, aspect: 1, ready: false };
    textures.set(url, rec);
    const img = new Image();
    img.decoding = 'async';
    img.onload = () => {
      const t = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, t);
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
      gl.generateMipmap(gl.TEXTURE_2D);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      Object.assign(rec, { tex: t, aspect: img.naturalWidth / img.naturalHeight, ready: true });
    };
    img.src = url;
    return rec;
  }

  let pal, bgLin, bgRgb;
  function setPalette(p) {
    pal = {
      ramp: new Float32Array(p.ramp.flatMap(hexToLin)),
      fringe: new Float32Array(p.fringe.flatMap(hexToLin)),
      chroma: p.chroma,
    };
    bgLin = hexToLin(p.bg);
    bgRgb = hexToRgb(p.bg);
  }
  setPalette(palette);

  let dpr = 1, cssW = 1, cssH = 1;
  function resize(w, h, maxDpr) {
    dpr = Math.min(window.devicePixelRatio || 1, maxDpr);
    cssW = w; cssH = h;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
  }

  function common(prog, time, tune) {
    gl.uniform1f(prog.u.uTime, time);
    gl.uniform3fv(prog.u.uRamp, pal.ramp);
    gl.uniform3fv(prog.u.uFringe, pal.fringe);
    gl.uniform1f(prog.u.uChroma, pal.chroma);
    gl.uniform4f(prog.u.uTune, tune.ribs, tune.foil, tune.grain, tune.aura);
  }

  const verts = new Float32Array(24);
  function drawBand(card, time, tune, full) {
    const u = band.u;
    gl.uniform1i(u.uVariant, card.variant);
    gl.uniform2f(u.uSize, card.w, card.bandH);
    gl.uniform1f(u.uRadius, card.radius);
    gl.uniform1f(u.uMask, full ? 0 : 1);
    gl.uniform1f(u.uAspect, card.w / card.bandH);
    gl.uniform2f(u.uTilt, card.tilt[0], card.tilt[1]);
    gl.uniform1f(u.uHolo, card.holo || 0);
    gl.uniform1f(u.uRev, card.rev);
    gl.uniform1f(u.uDim, full ? 0 : card.dim);
    gl.uniform3f(u.uBg, bgLin[0], bgLin[1], bgLin[2]);
    gl.uniform1f(u.uSeed, card.seed);
    gl.uniform1f(u.uFull, full ? 1 : 0);
    const tex = card.img ? loadTexture(card.img) : null;
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, tex ? tex.tex : blank);
    gl.uniform1i(u.uTex, 0);
    gl.uniform1f(u.uTexAspect, tex ? tex.aspect : 1);
    if (full) {
      // NDC quad; uv v=0 at the top.
      verts.set([-1, 1, 1, 0, 0, 0,  1, 1, 1, 0, 1, 0,  -1, -1, 1, 0, 0, 1,  1, -1, 1, 0, 1, 1]);
    } else {
      const q = card.quad; // [tl, tr, bl, br] each [x, y, w]
      verts.set([
        q[0][0], q[0][1], q[0][2], 0, 0, 0,
        q[1][0], q[1][1], q[1][2], 0, 1, 0,
        q[2][0], q[2][1], q[2][2], 0, 0, 1,
        q[3][0], q[3][1], q[3][2], 0, 1, 1,
      ]);
    }
    gl.bindVertexArray(bandVao);
    gl.bindBuffer(gl.ARRAY_BUFFER, bandBuf);
    gl.bufferSubData(gl.ARRAY_BUFFER, 0, verts);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }

  function blurPass(src, dst, off) {
    gl.bindFramebuffer(gl.FRAMEBUFFER, dst.fb);
    gl.viewport(0, 0, dst.w, dst.h);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, src.tex);
    gl.uniform1i(blur.u.uSrc, 0);
    gl.uniform2f(blur.u.uTexel, 1 / src.w, 1 / src.h);
    gl.uniform1f(blur.u.uOff, off);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }

  function drawAura(card, weight, time, tune, shape) {
    // 1. band into the small raw target, no mask, no dim
    gl.disable(gl.BLEND);
    gl.useProgram(band.p);
    common(band, time, tune);
    gl.uniform2f(band.u.uView, cssW, cssH);
    gl.bindFramebuffer(gl.FRAMEBUFFER, raw.fb);
    gl.viewport(0, 0, raw.w, raw.h);
    gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
    drawBand({ ...card, rev: card.rev }, time, tune, true);
    // 2. blur chain
    gl.useProgram(blur.p);
    gl.bindVertexArray(quadVao);
    blurPass(raw, lightA, 0.5);
    blurPass(lightA, lightB, 1.5);
    blurPass(lightB, heavyA, 1.5);
    blurPass(heavyA, heavyB, 2.5);
    blurPass(heavyB, heavyA, 3.5);
    // 3. composite into the canvas
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    gl.useProgram(aura.p);
    gl.uniform2f(aura.u.uView, cssW, cssH);
    const b = card.bbox;
    const bw = b[2] - b[0], bh = b[3] - b[1];
    gl.uniform4f(aura.u.uBand, b[0], b[1], b[2], b[3]);
    gl.uniform1f(aura.u.uCardBottom, card.bottom);
    gl.uniform1f(aura.u.uWeight, weight * card.rev);
    gl.uniform4f(aura.u.uTune, tune.ribs, tune.foil, tune.grain, tune.aura);
    gl.uniform2f(aura.u.uAuraShape, shape.falloff, shape.glow);
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, lightB.tex); gl.uniform1i(aura.u.uLight, 0);
    gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, heavyA.tex); gl.uniform1i(aura.u.uHeavy, 1);
    const x0 = b[0] - bw * .55, x1 = b[2] + bw * .55;
    const y0 = b[1] - bh * shape.height, y1 = card.bottom + bh * .55;
    gl.bindVertexArray(auraVao);
    gl.bindBuffer(gl.ARRAY_BUFFER, auraBuf);
    gl.bufferSubData(gl.ARRAY_BUFFER, 0, new Float32Array([x0, y0, x1, y0, x0, y1, x1, y1]));
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    gl.activeTexture(gl.TEXTURE0);
  }

  // frame: { cards (far -> near), auras: [{card, weight}], time, tune, shape }
  function render(f) {
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.clearColor(bgRgb[0], bgRgb[1], bgRgb[2], 1);
    gl.clear(gl.COLOR_BUFFER_BIT);
    for (const a of f.auras) if (a.weight > 0.01) drawAura(a.card, a.weight, f.time, f.tune, f.shape);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    gl.useProgram(band.p);
    common(band, f.time, f.tune);
    gl.uniform2f(band.u.uView, cssW, cssH);
    for (const c of f.cards) drawBand(c, f.time, f.tune, false);
  }

  function clear() {
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.clearColor(bgRgb[0], bgRgb[1], bgRgb[2], 1);
    gl.clear(gl.COLOR_BUFFER_BIT);
  }

  return { resize, render, clear, setPalette, loadTexture, get dpr() { return dpr; } };
}
