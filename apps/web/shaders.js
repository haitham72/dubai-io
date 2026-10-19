// GLSL ES 3.0 sources for the Home v2 stage.
// Band looks are re-implemented from ideas in ShipSwift SWMetal
// (github.com/signerlabs/ShipSwift, MIT License, Copyright (c) signerlabs):
// SWGrainGradient / SWAnimatedMeshGradient (mesh), SWFoil + SWIntenseBling (foil),
// SWPolishedAluminum (alu). The silk ribs and the stage aura are our own.

const HEAD = /* glsl */`#version 300 es
precision highp float;
`;

// Shared helpers: noise, palette ramp, thin-film fringe, dither.
const COMMON = /* glsl */`
uniform float uTime;
uniform vec3 uRamp[5];     // linear light, dark -> light
uniform vec3 uFringe[3];   // linear light
uniform float uChroma;     // 0 = cyan+purple fringe, 1 = full spectrum
uniform vec4 uTune;        // x rib frequency, y foil strength, z grain, w aura strength

float hash12(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }

// Ashima simplex noise 2D (MIT)
vec3 permute(vec3 x){ return mod(((x * 34.0) + 1.0) * x, 289.0); }
float snoise(vec2 v){
  const vec4 C = vec4(0.211324865405187, 0.366025403784439, -0.577350269189626, 0.024390243902439);
  vec2 i = floor(v + dot(v, C.yy));
  vec2 x0 = v - i + dot(i, C.xx);
  vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
  vec4 x12 = x0.xyxy + C.xxzz; x12.xy -= i1;
  i = mod(i, 289.0);
  vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0)) + i.x + vec3(0.0, i1.x, 1.0));
  vec3 m = max(0.5 - vec3(dot(x0, x0), dot(x12.xy, x12.xy), dot(x12.zw, x12.zw)), 0.0);
  m = m * m; m = m * m;
  vec3 x = 2.0 * fract(p * C.www) - 1.0;
  vec3 h = abs(x) - 0.5;
  vec3 ox = floor(x + 0.5);
  vec3 a0 = x - ox;
  m *= 1.79284291400159 - 0.85373472095314 * (a0 * a0 + h * h);
  vec3 g; g.x = a0.x * x0.x + h.x * x0.y; g.yz = a0.yz * x12.xz + h.yz * x12.yw;
  return 130.0 * dot(m, g);
}
float fbm(vec2 p){ float a = .5, s = 0.; for (int i = 0; i < 5; i++){ s += a * snoise(p); p = p * 2.03 + vec2(1.7, 9.2); a *= .5; } return s; }

vec3 ramp(float t){
  t = clamp(t, 0., 1.) * 4.;
  int i = int(floor(min(t, 3.999)));
  float f = smoothstep(0., 1., t - float(i));
  return mix(uRamp[i], uRamp[i + 1], f);
}
vec3 spectrum(float t){
  vec3 c = .5 + .5 * cos(6.28318 * (t + vec3(0., .33, .67)));
  return c * c; // ~linear
}
vec3 fringe(float t){
  float f = fract(t) * 3.;
  int i = int(floor(min(f, 2.999)));
  vec3 a = uFringe[i], b = uFringe[(i + 1) % 3];
  vec3 cyan = mix(a, b, smoothstep(0., 1., f - float(i)));
  return mix(cyan, spectrum(t), uChroma);
}
// interleaved gradient noise: kills 8-bit banding on soft gradients
float ign(vec2 p){ return fract(52.9829189 * fract(dot(p, vec2(.06711056, .00583715)))); }
vec3 toSRGB(vec3 c){
  c = c / (1. + c * .08);                 // gentle shoulder for speculars
  return pow(clamp(c, 0., 1.), vec3(1. / 2.2));
}
`;

// ---------------- band (card media) ----------------
export const BAND_VS = HEAD + /* glsl */`
layout(location = 0) in vec4 aPos;   // x, y (css px) , w (perspective), unused
layout(location = 1) in vec2 aUV;
uniform vec2 uView;                 // css px of the canvas
uniform float uFull;                // 1 = fullscreen quad for FBO pass
out vec2 vUV;
void main(){
  vUV = aUV;
  if (uFull > .5) { gl_Position = vec4(aPos.xy, 0., 1.); return; }
  vec2 ndc = vec2(aPos.x / uView.x * 2. - 1., 1. - aPos.y / uView.y * 2.);
  gl_Position = vec4(ndc * aPos.z, 0., aPos.z);
}`;

export const BAND_FS = HEAD + COMMON + /* glsl */`
in vec2 vUV;
out vec4 o;
uniform int uVariant;        // 0 silk, 1 mesh, 2 foil, 3 alu, 4 photo
uniform vec2 uSize;          // band size in card px (unscaled)
uniform float uRadius;       // card corner radius px
uniform float uMask;         // 1 = rounded top corners, 0 = full rect (FBO)
uniform float uAspect;       // band w / h
uniform vec2 uTilt;          // -1..1
uniform float uHolo;         // 0..1 foil overlay on top of any variant
uniform float uRev;          // reveal 0..1
uniform float uDim;          // 0..1 toward page background (side cards)
uniform vec3 uBg;            // page background, linear
uniform float uSeed;
uniform sampler2D uTex;
uniform float uTexAspect;    // texture w / h

vec3 silk(vec2 uv){
  // Smooth ribbed folds (carousel ref): low-frequency warp, soft rib profile.
  vec2 p = uv * vec2(uAspect, 1.) + uSeed;
  float t = uTime * .045;
  float w = snoise(p * .85 + vec2(t, -t * .7)) * .55 + snoise(p * 1.6 - vec2(t * .6, t)) * .22;
  float ang = 1.0 + .22 * snoise(p * .55 + t * .5) + uTilt.x * .22;
  vec2 dir = vec2(cos(ang), sin(ang));
  float r = dot(p, dir) + .34 * w;
  float ph = r * uTune.x + uTime * .30;
  float h = sin(ph) + .22 * sin(2. * ph + 1.3);
  float s = cos(ph) + .44 * cos(2. * ph + 1.3);
  vec3 n = normalize(vec3(-s * .55 * dir, 1.));
  vec3 L = normalize(vec3(.30 + uTilt.x * .9, .62 - uTilt.y * .9, .72));
  vec3 H = normalize(L + vec3(0., 0., 1.));
  float diff = .55 + .45 * dot(n, L);
  float spec = pow(max(dot(n, H), 0.), 64.);
  float fres = pow(1. - max(n.z, 0.), 1.5);
  vec3 base = ramp(.46 + .30 * w + .10 * h);
  vec3 film = fringe(r * 1.1 + w * .9 + n.x * 1.2 + uTilt.x * .6);
  vec3 col = base * diff;
  col = mix(col, film * 1.1, clamp(fres * 1.7 + .08, 0., .58));
  col += spec * (vec3(.85) + film * .7);
  col *= .80 + .20 * smoothstep(-1.2, .5, h);       // groove occlusion
  return col;
}

vec3 mesh(vec2 uv){
  float t = uTime * .07;
  vec2 p = uv + .07 * vec2(fbm(uv * 2.2 + t + uSeed), fbm(uv * 2.2 - t));
  vec2 c0 = vec2(.18 + .12 * sin(t * 1.3), .25 + .18 * cos(t));
  vec2 c1 = vec2(.82 + .10 * cos(t * .9), .30 + .15 * sin(t * 1.1));
  vec2 c2 = vec2(.45 + .20 * sin(t * .7), .85 + .08 * cos(t * 1.4));
  vec2 c3 = vec2(.75 + .10 * sin(t * 1.7), .78 + .10 * cos(t * .8));
  float w0 = 1. / (.02 + pow(distance(p, c0), 2.2));
  float w1 = 1. / (.02 + pow(distance(p, c1), 2.2));
  float w2 = 1. / (.02 + pow(distance(p, c2), 2.2));
  float w3 = 1. / (.02 + pow(distance(p, c3), 2.2));
  vec3 col = (ramp(.15) * w0 + ramp(.62) * w1 + ramp(.92) * w2 + fringe(.55 + t * .2) * w3) / (w0 + w1 + w2 + w3);
  float g = hash12(gl_FragCoord.xy + fract(uTime) * 91.) - .5;
  return col * (1. + g * uTune.z);                   // film grain
}

vec3 alu(vec2 uv){
  float brush = fbm(vec2(uv.x * 1.4 + uSeed, uv.y * 150.)) * .5 + .5;
  float fine = hash12(vec2(floor(uv.y * 700.), 3.1));
  vec3 base = mix(vec3(.30, .34, .37), vec3(.70, .76, .80), brush * .7 + fine * .3);
  base = mix(base, base * ramp(.75) * 1.6, .25);
  float y0 = .45 + uTilt.y * .55 + .08 * sin(uv.x * 3. + uTilt.x * 2.);
  float streak = exp(-pow((uv.y - y0) * 5.5, 2.));
  float streak2 = exp(-pow((uv.y - y0 - .32) * 9., 2.)) * .5;
  vec3 col = base * (.68 + .7 * (streak + streak2));
  col += (streak + streak2) * .25 * fringe(uv.x * .8 + uTilt.x * .5);
  return col;
}

vec3 photo(vec2 uv){
  vec2 tuv = uv;
  float a = uAspect / uTexAspect;                   // cover fit
  if (a > 1.) tuv.y = (uv.y - .5) / a + .5; else tuv.x = (uv.x - .5) * a + .5;
  tuv += uTilt * vec2(-.012, .010);                 // tiny parallax under tilt
  vec3 c = texture(uTex, tuv).rgb;
  c = c * c * (1.04);                               // ~sRGB -> linear, slight lift
  c = mix(c, c * c * (3. - 2. * c), .12);           // contrast curve
  c *= mix(.42, 1., smoothstep(0., .62, uv.y));     // top scrim for the headline
  c *= mix(.80, 1., smoothstep(1., .82, uv.y));     // soft bottom scrim
  return c;
}

vec3 foilOver(vec2 uv, vec3 base, float k){
  // Holographic sheen (SWFoil idea): a few soft spectral bands that slide with
  // tilt, plus sparse twinkles. Base stays readable; the foil rides on top.
  float a = dot(uv - .5, normalize(vec2(1., -.62))) * 2.2 + uTilt.x * 1.6 + uTilt.y * .9;
  float n = fbm(uv * 2.4 + uSeed) * .22;
  float bands = .5 + .5 * sin((a + n) * 6.28318 * 1.1);
  float sheen = smoothstep(.55, 1., bands);
  vec3 spec = fringe(a * .8 + n + .15);
  vec3 c = base + spec * sheen * .42 * k * uTune.y;
  c = mix(c, c * (1. + .25 * sheen), k);
  vec2 g = uv * vec2(uAspect, 1.) * 120.;
  float s = hash12(floor(g) + uSeed);
  float tw = step(.994, s) * pow(.5 + .5 * sin(uTime * 2.6 + s * 40. + uTilt.x * 16.), 12.);
  c += k * uTune.y * tw * 1.3 * (.6 + .4 * spec);
  return c;
}

float sdRoundBox(vec2 p, vec2 b, float r){ vec2 q = abs(p) - b + r; return length(max(q, 0.)) + min(max(q.x, q.y), 0.) - r; }

void main(){
  vec2 uv = vUV;
  vec3 col;
  if (uVariant == 0) col = silk(uv);
  else if (uVariant == 1) col = mesh(uv);
  else if (uVariant == 2) col = silk(uv) * .85;
  else if (uVariant == 3) col = alu(uv);
  else col = photo(uv);
  if (uHolo > 0.) col = foilOver(uv, col, uHolo);

  // reveal: a soft diagonal ink sweep with a thin-film leading edge
  float v = uv.x * .42 + (1. - uv.y) * .58 + .22 * fbm(uv * 3.2 + uSeed);
  float e = uRev * 1.75 - .30;
  float alpha = uRev >= .999 ? 1. : 1. - smoothstep(e - .10, e, v);
  float edge = exp(-abs(v - e + .05) * 26.) * (1. - step(.999, uRev));
  col += edge * fringe(v * 2. + uTime * .1) * 1.4;

  col = mix(col, uBg, uDim);

  float m = 1.;
  if (uMask > .5){
    vec2 px = uv * uSize;
    vec2 half_ = vec2(uSize.x * .5, (uSize.y + uRadius) * .5);
    float d = sdRoundBox(px - half_, half_, uRadius);
    m = clamp(.5 - d / max(fwidth(d), 1e-3), 0., 1.);
  }
  float a = alpha * m;
  vec3 srgb = toSRGB(col) + (ign(gl_FragCoord.xy) - .5) / 255.;
  o = vec4(srgb * a, a);
}`;

// ---------------- blur (dual-filter Kawase) ----------------
export const QUAD_VS = HEAD + /* glsl */`
layout(location = 0) in vec2 aPos;
out vec2 vUV;
void main(){ vUV = aPos * .5 + .5; gl_Position = vec4(aPos, 0., 1.); }`;

export const BLUR_FS = HEAD + /* glsl */`
in vec2 vUV; out vec4 o;
uniform sampler2D uSrc; uniform vec2 uTexel; uniform float uOff;
void main(){
  vec2 d = uTexel * (uOff + .5);
  vec4 c = texture(uSrc, vUV) * 4.;
  c += texture(uSrc, vUV + vec2(-d.x, -d.y));
  c += texture(uSrc, vUV + vec2( d.x, -d.y));
  c += texture(uSrc, vUV + vec2(-d.x,  d.y));
  c += texture(uSrc, vUV + vec2( d.x,  d.y));
  o = c / 8.;
}`;

// ---------------- aura (top reflection + bottom glow) ----------------
export const AURA_VS = HEAD + /* glsl */`
layout(location = 0) in vec2 aPos;  // css px
uniform vec2 uView;
out vec2 vPx;
void main(){ vPx = aPos; gl_Position = vec4(aPos.x / uView.x * 2. - 1., 1. - aPos.y / uView.y * 2., 0., 1.); }`;

export const AURA_FS = HEAD + /* glsl */`
in vec2 vPx; out vec4 o;
uniform sampler2D uLight;   // lightly blurred band (sRGB, premultiplied)
uniform sampler2D uHeavy;   // heavily blurred band
uniform vec4 uBand;         // left, top, right, bottom of the band (css px)
uniform float uCardBottom;  // css px
uniform float uWeight;      // 0..1 (which card is centred)
uniform vec4 uTune;         // w = aura strength
uniform vec2 uAuraShape;    // x height falloff, y glow strength
float ign(vec2 p){ return fract(52.9829189 * fract(dot(p, vec2(.06711056, .00583715)))); }
vec3 sat(vec3 c, float s){ float l = dot(c, vec3(.299, .587, .114)); return mix(vec3(l), c, s); }
void main(){
  float bw = uBand.z - uBand.x, bh = uBand.w - uBand.y;
  float u = (vPx.x - uBand.x) / bw;
  vec4 acc = vec4(0.);

  // Top: the band reflected upward past its top edge, blurring and widening
  // with distance, like light thrown off the card onto the page.
  float dy = (uBand.y - vPx.y) / bh;
  if (dy > -.03){
    float d = max(dy, 0.);
    float uu = .5 + (u - .5) / (1. + .65 * d);
    float vv = clamp(d * .85, .01, .97);          // mirror about the top edge
    vec4 cl = texture(uLight, vec2(uu, 1. - vv));
    vec4 ch = texture(uHeavy, vec2(uu, 1. - vv));
    vec4 c = mix(cl, ch, smoothstep(0., .32, d));
    float hx = abs(uu - .5) * 2.;
    float side = 1. - smoothstep(.70 + .20 * d, 1.08 + .25 * d, hx);
    float fall = exp(-d * uAuraShape.x) * side;
    float a = fall * uTune.w * uWeight;
    vec3 rgb = c.a > 1e-4 ? sat(c.rgb / c.a, 1.35) : vec3(0.);
    acc = vec4(rgb * a, a) * smoothstep(-.03, .02, dy);
  }

  // Bottom: a faint coloured glow under the card, as if on a glossy floor.
  float db = (vPx.y - uCardBottom) / bh;
  if (db > 0.){
    vec4 c = texture(uHeavy, vec2(clamp(u, .02, .98), .5));
    float hx = abs(u - .5) * 2.;
    float a = exp(-db * 9.) * (1. - smoothstep(.45, 1.05, hx)) * uAuraShape.y * uWeight;
    vec3 rgb = c.a > 1e-4 ? sat(c.rgb / c.a, 1.5) : vec3(0.);
    acc += vec4(rgb * a, a) * (1. - acc.a);
  }
  acc.rgb += (ign(gl_FragCoord.xy) - .5) / 255. * acc.a;
  o = acc;
}`;

export const VARIANT = { silk: 0, mesh: 1, foil: 2, alu: 3, photo: 4 };
