/* ===== Utilidades compartidas por el informe y la lista de criterios =====
   Todas las reglas (filtros, banderas, rampas de puntaje) vienen de D, que a su vez
   se extrajo del código con scripts/18_extraer_reglas.py. Aquí no hay umbrales. */
const SVGNS = "http://www.w3.org/2000/svg";
function el(tag, attrs, text) {
  const e = document.createElementNS(SVGNS, tag);
  for (const k in (attrs || {})) e.setAttribute(k, attrs[k]);
  if (text != null) e.textContent = text;
  return e;
}
function h(tag, attrs, html) {
  const e = document.createElement(tag);
  for (const k in (attrs || {})) {
    if (k === "class") e.className = attrs[k]; else e.setAttribute(k, attrs[k]);
  }
  if (html != null) e.innerHTML = html;
  return e;
}
const $ = (s, r) => (r || document).querySelector(s);
const $$ = (s, r) => Array.prototype.slice.call((r || document).querySelectorAll(s));
const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const THIN = " ";
const fmtInt = n => Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, THIN);
const num = x => String(+Number(x).toFixed(3));

function titleCase(s) {
  if (!s) return "";
  return s.replace(/\s*-\s*AUT\s*$/i, "").toLocaleLowerCase("es")
    .replace(/(^|[\s\-(])([a-záéíóúñü])/g, (m, a, b) => a + b.toLocaleUpperCase("es"))
    .replace(/ De /g, " de ").replace(/ Del /g, " del ");
}

const D_BY = {};
D.basins.forEach(b => { D_BY[b.id] = b; });
const POOL = D.basins.filter(b => b.pool);
const FONCE = D_BY[D.fonce];

/* Métricas que el código calcula y muestra pero NO usa en ninguna regla */
const EXTRA = {
  solape: {id: "solape", nombre: "Solape del caudal con IMERG", corto: "Solape con IMERG", campo: "imerg_years", unidad: "años",
           filtros: [], banderas: [], puntajes: [], porque: (D.no_usados.filter(n => n.id === "solape")[0] || {}).nota || "", fuente: "Serie diaria de caudal y ventana de IMERG"},
  px:     {id: "px", nombre: "Píxeles IMERG dentro de la cuenca", corto: "Píxeles IMERG", campo: "imerg_px", unidad: "píxeles",
           filtros: [], banderas: [], puntajes: [], porque: (D.no_usados.filter(n => n.id === "px")[0] || {}).nota || "", fuente: "Polígonos CAMELS-COL y grilla IMERG 0.1°"}
};
const CRIT = {};
D.criterios.forEach(c => { CRIT[c.id] = c; });
CRIT.solape = EXTRA.solape;
CRIT.px = EXTRA.px;

function nombreBasin(b) {
  const m = D.manual[String(b.id)];
  return m ? m.largo : titleCase(b.rio || "") + " @ " + titleCase(b.nombre || "");
}
function cortoBasin(b) {
  const m = D.manual[String(b.id)];
  return m ? m.corto : titleCase(b.rio || b.nombre || "");
}

/* Escala de visualización (solo presentación: dominio del eje, decimales, marcas redondas) */
const VIEW = {
  area:   {dom: [100, 10000], dec: 0, u: " km²",  ticks: [100, 300, 1000, 3000, 10000], log: true},
  anios:  {dom: [24, 43],     dec: 1, u: " años", ticks: [30, 35, 40]},
  falt:   {dom: [0, 10.5],    dec: 1, u: " %",    ticks: [0, 2, 4, 6, 8]},
  falt_p: {dom: [0, 10.5],    dec: 1, u: " %",    ticks: [0, 5]},
  hueco:  {dom: [0, 370],     dec: 0, u: " d",    ticks: [0, 100, 200, 300]},
  sub:    {dom: [-0.5, 7],    dec: 0, u: "",      ticks: [0, 1, 2, 4, 5, 6, 7]},
  cob:    {dom: [0.9, 1],     dec: 0, u: " %",    ticks: [], pct: true},
  fase:   {dom: [-0.6, 1],    dec: 2, u: "",      ticks: [-0.5, 0, 1]},
  rmes:   {dom: [-0.1, 1],    dec: 2, u: "",      ticks: [0, 0.5]},
  rrcv:   {dom: [0, 0.6],     dec: 2, u: "",      ticks: [0, 0.2, 0.4, 0.6]},
  rr:     {dom: [0, 2.2],     dec: 2, u: "",      ticks: [0, 0.5, 1.5, 2]},
  urb:    {dom: [0, 3.5],     dec: 2, u: " %",    ticks: [0, 1, 3]},
  agua:   {dom: [0, 3.5],     dec: 2, u: " %",    ticks: [0, 1, 3]},
  esc:    {dom: [-50, 50],    dec: 1, u: " %",    ticks: [-50, 0, 50], sign: true},
  flat:   {dom: [0, 10],      dec: 2, u: " %",    ticks: [0, 2.5, 7.5, 10]},
  solape: {dom: [8, 25.2],    dec: 1, u: " años", ticks: [10, 15, 20, 25]},
  px:     {dom: [1, 100],     dec: 0, u: " px",   ticks: [1, 3, 10, 30, 100], log: true}
};

function fmtVal(c, v) {
  if (v == null || isNaN(v)) return "—";
  const f = VIEW[c.id];
  if (!f) return String(v);
  if (f.pct) return (v * 100).toFixed(0) + " %";
  if (c.id === "area") return fmtInt(v) + " km²";
  let s = Number(v).toFixed(f.dec);
  if (f.sign && v > 0) s = "+" + s;
  return s + f.u;
}

/* ---- reglas: evaluación literal de lo que dice el código ---- */
function aplica(op, x, v) {
  switch (op) {
    case "<": return x < v; case "<=": return x <= v;
    case ">": return x > v; case ">=": return x >= v; case "==": return x === v;
  }
  return false;
}
function filtroFalla(f, v) { return f.op === "between" ? (v < f.min || v > f.max) : !aplica(f.op, v, f.valor); }
function banderaActiva(b, v) { return aplica(b.op, b.abs ? Math.abs(v) : v, b.valor); }

/* pass/fail (filtros) | flag/ok (banderas) | none (sin regla de descarte ni alerta) | na */
function evalCrit(c, v) {
  if (v == null || isNaN(v)) return "na";
  if (c.filtros.length) return c.filtros.some(f => filtroFalla(f, v)) ? "fail" : "pass";
  if (c.banderas.length) return c.banderas.some(b => banderaActiva(b, v)) ? "flag" : "ok";
  return "none";
}
const ST_ICON = {pass: "✓", fail: "✕", flag: "⚑", ok: "", none: "", na: "–"};
const ST_LABEL = {pass: "cumple el filtro", fail: "no cumple el filtro", flag: "bandera activa", ok: "sin bandera", none: "", na: "sin dato"};

function umbrales(c) {
  const s = [];
  const add = v => { if (s.indexOf(v) < 0) s.push(v); };
  c.filtros.forEach(f => { if (f.op === "between") { add(f.min); add(f.max); } else add(f.valor); });
  c.banderas.forEach(b => { add(b.valor); if (b.abs) add(-b.valor); });
  return s;
}

/* Zonas del eje según filtros (rojo) y banderas (ámbar) */
function zonesFor(c, dom) {
  const d0 = dom[0], d1 = dom[1], Z = [], seen = {};
  const add = (a, b, s) => {
    a = Math.max(a, d0); b = Math.min(b, d1);
    const k = a + "|" + b + "|" + s;
    if (b > a && !seen[k]) { seen[k] = 1; Z.push({a: a, b: b, s: s}); }
  };
  c.filtros.forEach(f => {
    if (f.op === "between") { add(d0, f.min, "fail"); add(f.max, d1, "fail"); }
    else if (f.op === "<=" || f.op === "<") add(f.valor, d1, "fail");
    else add(d0, f.valor, "fail");
  });
  c.banderas.forEach(b => {
    if (b.op === "<" || b.op === "<=") add(d0, b.valor, "flag");
    else { add(b.valor, d1, "flag"); if (b.abs) add(d0, -b.valor, "flag"); }
  });
  return Z;
}
const ZCOL = {fail: "var(--bad)", flag: "var(--warn)"};

/* Rampa de puntaje (polilínea extraída del código) */
function curveOf(c) { return c.puntajes && c.puntajes.length ? c.puntajes[0].curva : null; }
function interp(curve, v) {
  const n = curve.length;
  if (v <= curve[0][0]) return curve[0][1];
  if (v >= curve[n - 1][0]) return curve[n - 1][1];
  for (let i = 1; i < n; i++) {
    if (v <= curve[i][0]) {
      const x0 = curve[i - 1][0], y0 = curve[i - 1][1], x1 = curve[i][0], y1 = curve[i][1];
      return y0 + (y1 - y0) * (v - x0) / (x1 - x0);
    }
  }
  return curve[n - 1][1];
}
/* Puntos que da una métrica: producto de factores si el componente es un producto */
function pointsOf(c, v) {
  if (v == null || !c.puntajes.length) return null;
  return interp(c.puntajes[0].curva, v);
}

/* «Mejor» se deduce de la propia regla: rampa creciente/decreciente/con pico, o sentido de la bandera */
function direction(c) {
  const cv = curveOf(c);
  if (cv) {
    const ys = cv.map(p => p[1]), mx = Math.max.apply(null, ys);
    if (ys[0] < mx && ys[ys.length - 1] < mx) return {t: "peak", x: cv[ys.indexOf(mx)][0]};
    return ys[ys.length - 1] > ys[0] ? {t: "up"} : {t: "down"};
  }
  if (c.banderas.length) {
    const b = c.banderas[0];
    if (b.abs) return {t: "abs"};
    return (b.op === "<" || b.op === "<=") ? {t: "up"} : {t: "down"};
  }
  if (c.filtros.length) {
    const f = c.filtros[0];
    if (f.op === "between") return null;
    return (f.op === "<=" || f.op === "<") ? {t: "down"} : {t: "up"};
  }
  if (c.id === "solape") return {t: "up"};
  return null;
}
const DIRC = {};
Object.keys(CRIT).forEach(k => { DIRC[k] = direction(CRIT[k]); });
function goodOf(c, v) {
  const d = DIRC[c.id];
  if (!d || v == null) return null;
  if (d.t === "up") return v;
  if (d.t === "down") return -v;
  if (d.t === "abs") return -Math.abs(v);
  return -Math.abs(v - d.x);
}

/* Marcas del eje: umbrales de las reglas + puntos de quiebre de la rampa + marcas redondas */
function ticksFor(c) {
  const V = VIEW[c.id], d0 = V.dom[0], d1 = V.dom[1];
  const X = makeScale(c.id, 0, 1);
  const fuertes = umbrales(c).slice();
  const cv = curveOf(c);
  if (cv) cv.slice(1, -1).forEach(p => { if (fuertes.indexOf(p[0]) < 0) fuertes.push(p[0]); });
  const dentro = fuertes.filter(t => t >= d0 && t <= d1);
  const out = dentro.map(t => ({v: t, fuerte: true}));
  V.ticks.forEach(t => {
    if (!dentro.some(u => Math.abs(X(u) - X(t)) < 0.06)) out.push({v: t, fuerte: false});
  });
  return out;
}

function makeScale(id, x0, x1) {
  const V = VIEW[id], d0 = V.dom[0], d1 = V.dom[1];
  return v => {
    const vv = Math.min(Math.max(v, d0), d1);
    const t = V.log ? (Math.log(vv) - Math.log(d0)) / (Math.log(d1) - Math.log(d0)) : (vv - d0) / (d1 - d0);
    return x0 + t * (x1 - x0);
  };
}

/* Bloque de código con archivo y líneas reales */
function codeBlock(sn, titulo) {
  const lines = String(sn.codigo).split("\n");
  const body = lines.map((l, i) => '<span class="ln">' + (sn.desde + i) + "</span>" + esc(l)).join("\n");
  return '<figure class="code"><figcaption><span class="mono">' + esc(sn.archivo) + ":" + sn.desde +
    (sn.hasta !== sn.desde ? "–" + sn.hasta : "") + "</span>" + (titulo ? " · " + esc(titulo) : "") +
    "</figcaption><pre><code>" + body + "</code></pre></figure>";
}

/* Regla visual compacta: zonas, rampa de puntaje y marcas */
function ruler(c) {
  const V = VIEW[c.id];
  if (!V || V.pct) return null;
  const Z = zonesFor(c, V.dom), cv = curveOf(c);
  if (!Z.length && !cv) return null;
  const W = 300, H = 74, x0 = 10, x1 = W - 10, top = 6, base = 46, X = makeScale(c.id, x0, x1);
  const svg = el("svg", {viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": "Zonas y puntaje de " + c.corto, "class": "ruler"});
  Z.forEach(z => {
    svg.appendChild(el("rect", {x: X(z.a), y: top, width: Math.max(1, X(z.b) - X(z.a)), height: base - top, fill: ZCOL[z.s], "fill-opacity": 0.16}));
  });
  svg.appendChild(el("line", {x1: x0, x2: x1, y1: base, y2: base, stroke: "var(--rule-2)"}));
  if (cv) {
    const xs = cv.map(p => p[0]), lo = V.dom[0], hi = V.dom[1];
    const pts = [[lo, interp(cv, lo)]].concat(cv.filter(p => p[0] > lo && p[0] < hi)).concat([[hi, interp(cv, hi)]]);
    svg.appendChild(el("polyline", {points: pts.map(p => X(p[0]).toFixed(1) + "," + (base - p[1] * (base - top)).toFixed(1)).join(" "),
      fill: "none", stroke: "var(--accent)", "stroke-width": 2, "stroke-linejoin": "round"}));
  }
  ticksFor(c).forEach(t => {
    const x = X(t.v);
    svg.appendChild(el("line", {x1: x, x2: x, y1: base, y2: base + 4, stroke: t.fuerte ? "var(--ink-2)" : "var(--rule-2)"}));
    const anchor = x < x0 + 10 ? "start" : (x > x1 - 10 ? "end" : "middle");
    svg.appendChild(el("text", {x: x, y: base + 16, "text-anchor": anchor, "class": "tick-t", "font-weight": t.fuerte ? 600 : 400,
      fill: t.fuerte ? "var(--ink)" : "var(--faint)"}, (VIEW[c.id].sign && t.v > 0 ? "+" : "") + num(t.v)));
  });
  return svg;
}

/* Cómo se expresa cada regla en palabras (derivado de los datos extraídos, no escrito a mano) */
const OPS_TXT = {"<": "<", "<=": "≤", ">": ">", ">=": "≥", "==": "="};
function filtroTxt(f) {
  if (f.op === "between") return "entre " + fmtInt(f.min) + " y " + fmtInt(f.max);
  return OPS_TXT[f.op] + " " + num(f.valor);
}
function banderaTxt(b) { return (b.abs ? "|valor| " : "") + OPS_TXT[b.op] + " " + num(b.valor); }
function curvaTxt(cv) { return cv.map(p => num(p[0]) + " → " + num(p[1])).join(" · "); }

/* Componentes del puntaje y reglas de un criterio en palabras (compartido) */
const COMPN = {};
D.componentes.forEach(c => { COMPN[c.id] = c; });
const pct = x => num(x * 100) + " %";
function metricaDeCol(col) {
  return D.criterios.filter(x => x.columnas.indexOf(col) >= 0)[0] || null;
}
function CRIT_BY_COL(col) {
  const c = metricaDeCol(col);
  return c ? c.corto.toLowerCase() : col;
}
function reglasHTML(c) {
  const L = [];
  c.filtros.forEach(f => L.push(["Filtro", (f.etapa === "metadatos" ? "En los metadatos" : "En la serie diaria") + ": <b>" + esc(filtroTxt(f)) +
    "</b> <span class=\"src\">" + esc(f.col) + " · " + esc(f.archivo) + ":" + f.linea + "</span>"]));
  c.banderas.forEach(b => L.push(["Bandera", "«" + esc(b.nombre) + "»: <b>" + esc(banderaTxt(b)) + "</b> <span class=\"src\">" +
    esc(b.col) + " · 16_analisis_completo.py:" + b.linea + "</span>"]));
  c.puntajes.forEach(p => {
    const comp = COMPN[p.comp];
    const parte = p.producto ? "Factor del producto que forma" : (p.peso === 1 ? "Es todo el componente" : "Aporta " + pct(p.peso) + " del componente");
    L.push(["Puntaje", parte + " <b>" + esc(comp.nombre) + "</b> (" + pct(comp.peso) + " del total). Puntos por valor: <b>" + esc(curvaTxt(p.curva)) +
      "</b> <span class=\"src\">" + esc(p.columna) + "</span>"]);
  });
  if (!L.length) L.push(["Sin regla", "El código lo calcula pero no lo usa."]);
  return '<ul class="rules">' + L.map(r => '<li><span class="k">' + r[0] + "</span><span>" + r[1] + "</span></li>").join("") + "</ul>";
}
