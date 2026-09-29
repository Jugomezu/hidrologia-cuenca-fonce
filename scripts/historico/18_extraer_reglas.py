"""Extrae las REGLAS de seleccion directamente del codigo que se ejecuto.

Nada de umbrales retipeados: se leen con `ast` de
    scripts/historico/13_preliminar.py       (filtros)
    scripts/historico/16_analisis_completo.py (subcuenca valida, banderas, puntaje, ranking)
    scripts/historico/10a_geometria.py       (anidamiento y rango de area de subcuencas)
y cada regla conserva archivo, lineas y el codigo textual.

Despues VERIFICA que las reglas extraidas reproducen los resultados guardados:
  - filtro de metadatos  -> las 174 cuencas de out/preliminar_v2.csv
  - filtro de series     -> las 134 con pasa_series
  - banderas             -> columna `banderas` de out/analisis_174.csv
  - subcuenca valida     -> columna n_sub_ok
  - puntaje              -> columnas s_* y score (se evalua el codigo original)
  - ranking              -> igual al de out/analisis_completo.csv
Si algo no coincide, el script se detiene.

Salida: out/reglas_extraidas.json
"""
import ast, copy, json, re
from pathlib import Path
import numpy as np, pandas as pd

SC = Path("scripts")
ARCH = {"13": "13_preliminar.py", "16": "16_analisis_completo.py", "10a": "10a_geometria.py"}
FUENTE = {}
for k, f in ARCH.items():
    src = (SC / f).read_text(encoding="utf-8")
    FUENTE[k] = dict(archivo=f, src=src, lineas=src.splitlines(), tree=ast.parse(src))

OPS = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "=="}

# ------------------------------------------------------------------ utilidades
def snippet(k, node):
    F = FUENTE[k]
    return dict(archivo=F["archivo"], desde=node.lineno, hasta=node.end_lineno,
                codigo="\n".join(F["lineas"][node.lineno - 1: node.end_lineno]))

def col_of(n):
    """m["area"] / r["x"] / a["x"] -> 'area' | 'x'"""
    if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) and isinstance(n.slice.value, str):
        return n.slice.value
    return None

def comparaciones(node):
    """Todas las comparaciones `col <op> const` y `col.between(a, b)` dentro de un nodo."""
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Compare) and len(n.ops) == 1:
            left, ab = n.left, False
            if isinstance(left, ast.Call) and getattr(left.func, "id", None) == "abs" and left.args:
                left, ab = left.args[0], True
            col, c = col_of(left), n.comparators[0]
            if col and isinstance(c, ast.Constant) and isinstance(c.value, (int, float)):
                out.append(dict(col=col, op=OPS[type(n.ops[0])], valor=c.value, abs=ab, linea=n.lineno))
        elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "between"
              and len(n.args) == 2 and all(isinstance(x, ast.Constant) for x in n.args)):
            out.append(dict(col=col_of(n.func.value), op="between", min=n.args[0].value,
                            max=n.args[1].value, abs=False, linea=n.lineno))
    return out

def asignacion(k, nombre):
    for n in FUENTE[k]["tree"].body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) \
                and n.targets[0].id == nombre:
            return n
    raise KeyError(nombre)

def asignacion_col(k, col):
    for n in FUENTE[k]["tree"].body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and col_of(n.targets[0]) == col:
            return n
    raise KeyError(col)

def funcion(k, nombre):
    for n in FUENTE[k]["tree"].body:
        if isinstance(n, ast.FunctionDef) and n.name == nombre:
            return n
    raise KeyError(nombre)

def asignacion_en_cualquier_lugar(k, nombre):
    for n in ast.walk(FUENTE[k]["tree"]):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) \
                and n.targets[0].id == nombre:
            return n
    raise KeyError(nombre)

# ------------------------------------------------------------------ 1. filtros (13)
f1, f2 = asignacion("13", "f1"), asignacion("13", "f2")
filtros = [
    dict(etapa="metadatos", **snippet("13", f1), items=comparaciones(f1.value)),
    dict(etapa="series", **snippet("13", f2), items=comparaciones(f2.value)),
]

# ------------------------------------------------------------------ 2. subcuenca valida (16 y 10a)
sub_ok_fn = funcion("16", "sub_ok")
ret = sub_ok_fn.body[-1]                         # el `return` final, no el `return False` anidado
assert isinstance(ret, ast.Return) and not isinstance(ret.value, ast.Constant)
sub_valida = dict(**snippet("16", sub_ok_fn), items=comparaciones(ret.value))
assert len(sub_valida["items"]) == 2, sub_valida["items"]

utiles = asignacion_en_cualquier_lugar("10a", "utiles")
rng = [n for n in ast.walk(utiles) if isinstance(n, ast.Compare) and len(n.ops) == 2
       and isinstance(n.left, ast.Constant) and isinstance(n.comparators[1], ast.Constant)]
anidamiento = dict(
    sjoin=snippet("10a", asignacion_en_cualquier_lugar("10a", "j")),
    rango_area=dict(**snippet("10a", utiles), min=rng[0].left.value, max=rng[0].comparators[1].value),
)
# la 1.a asignacion a `j` es el sjoin; la 2.a filtra por area: tomar el bloque completo
j_nodes = [n for n in ast.walk(FUENTE["10a"]["tree"]) if isinstance(n, ast.Assign)
           and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "j"]
anidamiento["sjoin"] = dict(archivo=ARCH["10a"], desde=j_nodes[0].lineno, hasta=j_nodes[-1].end_lineno,
    codigo="\n".join(FUENTE["10a"]["lineas"][j_nodes[0].lineno - 1: j_nodes[-1].end_lineno]))

# ------------------------------------------------------------------ 3. banderas (16)
ban_fn = funcion("16", "banderas")
banderas = []
for n in ban_fn.body:
    if isinstance(n, ast.If):
        cmp_ = comparaciones(n.test)[0]
        call = n.body[0].value
        banderas.append(dict(nombre=call.args[0].value, linea=n.lineno, **{k: v for k, v in cmp_.items() if k != "linea"}))
banderas_snip = snippet("16", ban_fn)

# ------------------------------------------------------------------ 4. puntaje (16)
nz_def = funcion("16", "nz")
NZ_ENV = {"pd": pd, "np": np}
exec(ast.unparse(nz_def), NZ_ENV)                       # la nz() ORIGINAL del script
NZ = NZ_ENV["nz"]

def columnas(node):
    return sorted({col_of(n) for n in ast.walk(node) if col_of(n) and
                   isinstance(n, ast.Subscript) and getattr(n.value, "id", None) == "a"})

def constantes(node):
    return [n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, (int, float))]

def terminos(node):
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return terminos(node.left) + terminos(node.right)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult) and isinstance(node.left, ast.Constant):
        return [dict(peso=node.left.value, nodo=node.right)]
    return [dict(peso=1.0, nodo=node)]

def evaluar(node, env_a):
    e = ast.fix_missing_locations(ast.Expression(body=copy.deepcopy(node)))
    return eval(compile(e, "<regla>", "eval"), {"a": env_a, "nz": NZ, "np": np, "pd": pd})

def dp(xs, ys, eps):
    """Douglas-Peucker sobre (x, y)."""
    def rec(i, j):
        if j <= i + 1:
            return [i, j]
        x0, y0, x1, y1 = xs[i], ys[i], xs[j], ys[j]
        t = (xs[i + 1:j] - x0) / (x1 - x0 if x1 != x0 else 1)
        d = np.abs(ys[i + 1:j] - (y0 + t * (y1 - y0)))
        k = int(d.argmax())
        if d[k] <= eps:
            return [i, j]
        return rec(i, i + 1 + k)[:-1] + rec(i + 1 + k, j)
    return rec(0, len(xs) - 1)

A174 = pd.read_csv("out/analisis_174.csv")

def hoja(node):
    cols = columnas(node)
    assert len(cols) == 1, (ast.unparse(node), cols)
    col = cols[0]
    v = A174[col].dropna()
    consts = constantes(node)
    lo = min([v.min()] + consts)
    hi = min(v.max(), max(v.quantile(0.99) * 1.2, max(consts)))
    hi = max(hi, max(consts))
    xs = np.unique(np.r_[np.linspace(lo, hi, 241), [c for c in consts if lo <= c <= hi]])
    ys = np.asarray(evaluar(node, pd.DataFrame({col: xs})), float)
    idx = dp(xs, ys, 1e-3)
    puntos = [[round(float(xs[i]), 4), round(float(ys[i]), 4)] for i in idx]
    return dict(col=col, codigo=ast.unparse(node), curva=puntos)

def analiza(node):
    if (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult)
            and not isinstance(node.left, ast.Constant) and not isinstance(node.right, ast.Constant)):
        return dict(tipo="producto", factores=[hoja(node.left), hoja(node.right)], codigo=ast.unparse(node))
    return dict(tipo="hoja", **hoja(node))

score_asg = asignacion_col("16", "score")
comp_cols = {}
for t in terminos(score_asg.value):
    comp_cols[col_of(t["nodo"])] = t["peso"]                 # {'s_registro': 0.25, ...}

componentes = []
for col, peso in comp_cols.items():
    asg = asignacion_col("16", col)
    ts = terminos(asg.value)
    componentes.append(dict(
        col=col, peso=peso, **snippet("16", asg), nodo_codigo=ast.unparse(asg.value),
        terminos=[dict(peso=t["peso"], **analiza(t["nodo"])) for t in ts]))
puntaje = dict(nz=snippet("16", nz_def), componentes=componentes, score=snippet("16", score_asg),
               ranking=snippet("16", next(n for n in FUENTE["16"]["tree"].body if isinstance(n, ast.Assign)
                                          and isinstance(n.value, ast.Call) and
                                          getattr(n.value.func, "attr", "") == "sort_values"
                                          and "score" in ast.unparse(n.value))))

# puntaje preliminar de 13 (NO se uso para la decision final; se documenta)
prelim_asg = next(n for n in FUENTE["13"]["tree"].body if isinstance(n, ast.Assign) and col_of(n.targets[0]) == "score")
preliminar = snippet("13", prelim_asg)

# ------------------------------------------------------------------ 5. metricas (documentacion + reglas)
# Solo NOMBRES y textos; ningun numero. Los umbrales salen de lo extraido arriba.
DOC = [
 ("area",   "Área de la cuenca", "Área", "usuario", "area", "km²", ["area"],
  "Rango fijado por el usuario.", "CAMELS-COL: polígonos delineados con el DEM del IGAC (30 m)"),
 ("anios",  "Años de registro de caudal", "Años de registro", "usuario", "q_years", "años", ["n_years_obs", "q_years"],
  "Mínimo fijado por el usuario.", "CAMELS-COL: serie diaria de caudal de IDEAM"),
 ("falt",   "Datos diarios faltantes de caudal", "Faltantes de caudal", "usuario", "q_miss", "%", ["missing_pct", "q_miss"],
  "Límite fijado por el usuario, medido primero en los metadatos y luego en la serie diaria.", "CAMELS-COL: serie diaria de caudal de IDEAM"),
 ("falt_p", "Datos diarios faltantes de precipitación", "Faltantes de precipitación", "usuario", "pr_miss", "%", ["pr_miss"],
  "El usuario pidió el límite «por variable». La precipitación de CAMELS-COL es CHIRPS y no tiene faltantes.", "CAMELS-COL: precipitación CHIRPS v2 por cuenca"),
 ("hueco",  "Hueco continuo más largo de caudal", "Hueco máximo", "usuario", "q_gap_max", "días", ["q_gap_max"],
  "El usuario pidió «sin tramos muy largos» sin dar cifra: el umbral que ejecuta el código es una interpretación mía.", "CAMELS-COL: serie diaria de caudal de IDEAM"),
 ("sub",    "Subcuencas anidadas con datos", "Subcuencas válidas", "usuario", "n_sub_ok", "subcuencas", ["n_sub_ok"],
  "Plus pedido por el usuario: permite validar el modelo aguas arriba, sin depender solo de la estación de cierre.", "Geometría CAMELS-COL: aforo de la subcuenca dentro del polígono de la madre"),
 ("cob",    "Cobertura de IMERG sobre la cuenca", "Cobertura IMERG", "usuario", "imerg_cob", "fracción", ["imerg_cobertura"],
  "Requisito del usuario: que exista precipitación IMERG para la cuenca.", "IMERG Final mensual V07 (10.5067/GPM/IMERG/3B-MONTH/07)"),
 ("fase",   "Coherencia estacional lluvia–caudal (IMERG)", "Fase lluvia–caudal", "mio", "fase_imerg", "r", ["fase_imerg"],
  "Prueba de que el forzamiento y el aforo describen el mismo río; si es baja no hay modelo que calibrar.", "IMERG mensual promediado por cuenca + caudal IDEAM"),
 ("rmes",   "Correlación mensual lluvia–caudal (IMERG)", "Correlación mensual", "mio", "r_mes_imerg", "ρ", ["r_mes_imerg"],
  "Mide si los meses húmedos de la lluvia coinciden con los de caudal, no solo el ciclo medio.", "IMERG mensual promediado por cuenca + caudal IDEAM"),
 ("rrcv",   "Estabilidad del balance anual", "Estabilidad del balance", "mio", "RRcv_imerg", "CV", ["RRcv_imerg"],
  "Un balance que cambia mucho de un año a otro delata errores de aforo, cambios de rating o extracciones variables.", "IMERG mensual promediado por cuenca + caudal IDEAM"),
 ("rr",     "Coeficiente de escorrentía (IMERG)", "Escorrentía", "mio", "RR_imerg", "Q/P", ["RR_imerg"],
  "Q/P mayor que 1 es físicamente imposible a largo plazo; muy bajo indica extracciones o lluvia sobreestimada.", "IMERG mensual promediado por cuenca + caudal IDEAM"),
 ("urb",    "Área urbana", "Urbano", "mio", "urban_perc", "%", ["urban_perc"],
  "Indicador de intervención humana.", "CAMELS-COL: suelos del IGAC (zonas urbanas)"),
 ("agua",   "Cuerpos de agua", "Cuerpos de agua", "mio", "water_bodies_perc", "%", ["water_bodies_perc"],
  "Sustituto de embalses: CAMELS-COL no trae un atributo explícito de represas.", "CAMELS-COL: MapBiomas Colombia 2022"),
 ("esc",    "Cambio de escalón en el caudal", "Escalón", "mio", "escalon", "%", ["escalon"],
  "Un salto sostenido entre mitades del registro suele ser cambio de curva de calibración o extracción, no clima.", "Serie diaria de caudal de IDEAM (CAMELS-COL)"),
 ("flat",   "Días con caudal repetido (flatline)", "Valores repetidos", "mio", "flat", "%", ["flat"],
  "El caudal real no se repite siete días al milésimo: son datos rellenados o copiados.", "Serie diaria de caudal de IDEAM (CAMELS-COL)"),
]
COMP_ID = {"s_registro": ("reg", "Registro"), "s_subcuencas": ("sub", "Subcuencas"),
           "s_imerg": ("imerg", "Coherencia IMERG"), "s_balance": ("bal", "Balance hídrico"),
           "s_natural": ("nat", "Naturalidad")}

metricas = []
for id_, nombre, corto, origen, campo, unidad, cols, porque, fuente in DOC:
    m_ = dict(id=id_, nombre=nombre, corto=corto, origen=origen, campo=campo, unidad=unidad,
              columnas=cols, porque=porque, fuente=fuente, filtros=[], banderas=[], puntajes=[])
    for f in filtros:
        for it in f["items"]:
            if it["col"] in cols:
                m_["filtros"].append(dict(etapa=f["etapa"], archivo=f["archivo"], **it))
    for b in banderas:
        if b["col"] in cols:
            m_["banderas"].append(b)
    for c in componentes:
        for t in c["terminos"]:
            partes = t["factores"] if t["tipo"] == "producto" else [t]
            for p in partes:
                if p["col"] in cols:
                    m_["puntajes"].append(dict(
                        comp=COMP_ID[c["col"]][0], comp_col=c["col"], peso=(None if t["tipo"] == "producto" else t["peso"]),
                        producto=t["tipo"] == "producto", curva=p["curva"], codigo=p["codigo"], columna=p["col"]))
    metricas.append(m_)

# ------------------------------------------------------------------ 6. VERIFICACION
verif = {}
def aplica(op, x, v):
    return {"<": x < v, "<=": x <= v, ">": x > v, ">=": x >= v, "==": x == v}[op]

# 6.1 filtros de metadatos
master = pd.read_csv("out/camels_col_master.csv")
ok = pd.Series(True, index=master.index)
for it in filtros[0]["items"]:
    x = master[it["col"]]
    ok &= x.between(it["min"], it["max"]) if it["op"] == "between" else aplica(it["op"], x, it["valor"])
pre = pd.read_csv("out/preliminar_v2.csv")
assert set(master.loc[ok, "gauge_id"]) == set(pre["gauge_id"]), "filtro de metadatos NO reproduce las 174"
verif["metadatos"] = int(ok.sum())

# 6.2 filtros de series
ok2 = pd.Series(True, index=pre.index)
for it in filtros[1]["items"]:
    ok2 &= aplica(it["op"], pre[it["col"]], it["valor"])
assert (ok2 == pre["pasa_series"]).all(), "filtro de series NO reproduce pasa_series"
verif["series"] = int(ok2.sum())

# 6.3 banderas
A = A174.copy()
esperado = pd.Series("", index=A.index)
for b in banderas:
    x = A[b["col"]].abs() if b["abs"] else A[b["col"]]
    hit = aplica(b["op"], x, b["valor"]).fillna(False)
    esperado = np.where(hit, np.where(esperado == "", b["nombre"], esperado + ";" + b["nombre"]), esperado)
esperado = pd.Series(esperado, index=A.index)
assert (esperado == A["banderas"].fillna("")).all(), "banderas extraidas NO reproducen la columna banderas"
verif["banderas"] = int(len(A))

# 6.4 subcuenca valida
geo = pd.read_csv("out/geometria.csv").set_index("gauge_id")
mm = master.set_index("gauge_id")
def valida(s):
    if s not in mm.index: return False
    r = mm.loc[s]
    return all(bool(aplica(it["op"], r[it["col"]], it["valor"])) for it in sub_valida["items"])
def n_ok(g):
    if g not in geo.index or pd.isna(geo.loc[g, "subs"]) or geo.loc[g, "subs"] == "": return 0
    return sum(valida(int(s)) for s in str(geo.loc[g, "subs"]).split(";") if s)
assert (A["gauge_id"].map(n_ok) == A["n_sub_ok"]).all(), "subcuenca valida NO reproduce n_sub_ok"
verif["subcuenca_valida"] = int(len(A))

# 6.5 puntaje: se evalua el codigo ORIGINAL
maxdif = 0.0
Aeval = A.copy()
for c in componentes:
    y = np.asarray(evaluar(ast.parse(c["nodo_codigo"], mode="eval").body, Aeval), float)
    d = np.nanmax(np.abs(y - Aeval[c["col"]].to_numpy(float)))
    maxdif = max(maxdif, float(d))
    assert d < 1e-9, f"{c['col']} no reproduce"
sc = np.asarray(evaluar(ast.parse(ast.unparse(score_asg.value), mode="eval").body, Aeval), float)
assert np.nanmax(np.abs(sc - Aeval["score"].to_numpy(float))) < 1e-9, "score no reproduce"
verif["puntaje_maxdif"] = maxdif

# 6.6 ranking igual al de la corrida original (134)
orig = pd.read_csv("out/analisis_completo.csv")
pool = A[A["pasa_series"]].sort_values("score", ascending=False)
assert list(pool["gauge_id"]) == list(orig.sort_values("score", ascending=False)["gauge_id"]), "ranking distinto"
verif["ranking_pool"] = int(len(pool))
verif["primero"] = int(pool.iloc[0]["gauge_id"])

out = dict(archivos=[v["archivo"] for v in FUENTE.values()], filtros=filtros, sub_valida=sub_valida,
           anidamiento=anidamiento, banderas=banderas, banderas_snip=banderas_snip, puntaje=puntaje,
           preliminar=preliminar, metricas=metricas, comp_id={k: v[0] for k, v in COMP_ID.items()},
           comp_nombre={v[0]: v[1] for v in COMP_ID.values()}, verificacion=verif)
Path("out/reglas_extraidas.json").write_text(json.dumps(out, ensure_ascii=False, allow_nan=False), encoding="utf-8")

print("VERIFICACION OK:", json.dumps(verif, ensure_ascii=False))
print("\nFILTROS:")
for f in filtros:
    print(f"  [{f['etapa']}] {f['archivo']}:{f['desde']}-{f['hasta']}")
    for it in f["items"]:
        print("     ", {k: v for k, v in it.items() if k != "linea"})
print("SUBCUENCA VALIDA:", [{k: v for k, v in it.items() if k != 'linea'} for it in sub_valida["items"]],
      "| area subcuenca (fraccion):", anidamiento["rango_area"]["min"], "-", anidamiento["rango_area"]["max"])
print("BANDERAS:")
for b in banderas:
    print("     ", b)
print("PUNTAJE:")
for c in componentes:
    print(f"  {c['col']:<13s} peso {c['peso']}  ({c['archivo']}:{c['desde']}-{c['hasta']})")
    for t in c["terminos"]:
        if t["tipo"] == "producto":
            print("      producto:", [(f["col"], f["curva"]) for f in t["factores"]])
        else:
            print(f"      peso {t['peso']:<5} {t['col']:<13s} curva {t['curva']}")
