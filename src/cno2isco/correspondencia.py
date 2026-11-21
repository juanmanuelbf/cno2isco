"""Regla de decisión CNO-2001 -> CIUO-08 (ISCO-08) a 2 dígitos.

La metodología completa está en docs/metodologia.md. Para cada código CNO se
aplica, en este orden:

    1. directo              el código figura en la tabla del INDEC con un CIUO de 2 dígitos.
    2. por_actividad        la tabla sólo da el gran grupo (1 dígito); el 2.º dígito se
                            busca en la tabla auxiliar del INDEC según la rama (CAES).
    3. vecindad             el código no está en la tabla: se toman los códigos de la tabla
                            con igual carácter y calificación; si son al menos dos y todos
                            coinciden, se adopta ese CIUO.
    4. gran_grupo           sólo se pudo determinar el gran grupo (1 dígito).
    5. residual             carácter 99: no respuesta / no clasificable.
       fuera_de_catalogo    el código no existe en el CNO-2001.
       sin_correspondencia  código válido que ninguna regla resolvió.
       sin_codigo           ocupado sin código de ocupación.

Se aplica a la ocupación principal de los ocupados (PP04D_COD) y a la ocupación
anterior de los desocupados (PP11D_COD).
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources

import pandas as pd

COL_ESTADO = "ESTADO"
COL_OCUPACION = "PP04D_COD"   # ocupación principal de los ocupados, CNO-2001
COL_RAMA = "PP04B_COD"        # rama de esa ocupación, CAES
COL_OCUPACION_ANT = "PP11D_COD"   # ocupación anterior de los desocupados
COL_RAMA_ANT = "PP11B_COD"        # rama de la ocupación anterior
OCUPADO, DESOCUPADO = "1", "2"
MIN_VECINOS = 2
CARACTER_RESIDUAL = "99"

COLUMNAS_NUEVAS = [
    "cno01_fuente",
    "cno01_5d",
    "cno01_caracter",
    "cno01_caracter_desc",
    "cno01_jerarquia",
    "cno01_tecnologia",
    "cno01_calificacion",
    "isco08_2d",
    "isco08_2d_desc",
    "isco08_gran_grupo",
    "isco08_gran_grupo_desc",
    "isco08_metodo",
    "isco08_caso",
]

CASOS = {
    "directo": "1. INDEC - directa",
    "por_actividad": "2. INDEC - por actividad",
    "vecindad": "3. Ad hoc - 2 dígitos",
    "gran_grupo": "4. Ad hoc - 1 dígito",
    "residual": "5. Sin clasificación",
    "fuera_de_catalogo": "5. Sin clasificación",
    "sin_correspondencia": "5. Sin clasificación",
    "sin_codigo": "5. Sin clasificación",
}


def _leer(nombre: str) -> pd.DataFrame:
    with resources.files("cno2isco").joinpath("datos", nombre).open(encoding="utf-8") as fh:
        return pd.read_csv(fh, dtype=str, keep_default_na=False, na_values=[""])


@dataclass
class Tablas:
    """Tablas de correspondencia empaquetadas con cno2isco (carpeta datos/)."""

    directo: dict          # cno_5d -> "NN" (2 dígitos) o "*G" (sólo gran grupo G)
    caes: dict             # (gran_grupo, caes_2d) -> isco08_2d
    bloques: dict          # (caracter, calificacion) -> valor, para la regla de vecindad
    catalogo: set          # códigos válidos del CNO-2001
    subgrupos: set         # subgrupos de 2 dígitos que existen en la CIUO-08
    desc_2d: dict
    desc_gg: dict
    desc_caracter: dict

    @classmethod
    def cargar(cls) -> "Tablas":
        cw = _leer("cno2001_isco08.csv")
        caes = _leer("caes_isco08.csv")
        lab = _leer("isco08_2d.csv")
        gg = _leer("isco08_gran_grupo.csv")
        car = _leer("cno2001_caracter.csv")
        cat = _leer("cno2001_catalogo.csv")

        valor = cw["isco08_2d"].fillna("*" + cw["isco08_gran_grupo"])
        directo = dict(zip(cw["cno_5d"], valor))

        # Regla de vecindad, precalculada: para cada bloque (carácter, calificación)
        # se guarda el valor sólo si el bloque tiene MIN_VECINOS o más códigos y
        # todos coinciden. Jerarquía y tecnología quedan libres.
        bloques = {}
        for clave, vals in valor.groupby([cw["cno_5d"].str[:2], cw["cno_5d"].str[4]]):
            if len(vals) >= MIN_VECINOS and vals.nunique() == 1:
                bloques[clave] = vals.iloc[0]

        return cls(
            directo=directo,
            caes=dict(zip(zip(caes["isco08_gran_grupo"], caes["caes_2d"]), caes["isco08_2d"])),
            bloques=bloques,
            catalogo=set(cat["cno_5d"]),
            subgrupos=set(lab["isco08_2d"]),
            desc_2d=dict(zip(lab["isco08_2d"], lab["descripcion"])),
            desc_gg=dict(zip(gg["isco08_gran_grupo"], gg["descripcion"])),
            desc_caracter=dict(zip(car["caracter"], car["descripcion"])),
        )


_TABLAS: Tablas | None = None


def tablas() -> Tablas:
    global _TABLAS
    if _TABLAS is None:
        _TABLAS = Tablas.cargar()
    return _TABLAS


# --------------------------------------------------------------------------- #
# Normalización de códigos
# --------------------------------------------------------------------------- #
def _limpiar(serie: pd.Series) -> pd.Series:
    s = serie.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    return s.mask(s.isin(["", "nan", "None", "<NA>"]))


def normalizar_cno(serie: pd.Series) -> pd.Series:
    """Código CNO a 5 dígitos. Al exportarse pierde los ceros a la izquierda
    (p. ej. 5002 -> 05002)."""
    return _limpiar(serie).str.zfill(5)


def division_caes(serie: pd.Series) -> pd.Series:
    """División CAES (2 dígitos) a partir de PP04B_COD.

    El código viene a 4 dígitos (4803), a 3 si perdió el cero inicial (101 ->
    0101) o a 1-2 dígitos cuando sólo se conoce la división (48, 1 -> 01).
    """
    s = _limpiar(serie)
    corto = s.str.len() <= 2
    return s.str.zfill(2).where(corto, s.str.zfill(4).str[:2])


# --------------------------------------------------------------------------- #
# Asignación
# --------------------------------------------------------------------------- #
def asignar(cno: pd.Series, rama: pd.Series, t: Tablas | None = None) -> pd.DataFrame:
    """Aplica la regla de decisión a una serie de códigos CNO ya normalizados.

    Devuelve un DataFrame con `isco08_2d`, `isco08_gran_grupo` e `isco08_metodo`,
    con el mismo índice que `cno`.
    """
    t = t or tablas()
    idx = cno.index
    rama2 = division_caes(rama)

    valor = cno.map(t.directo).astype("object")
    metodo = pd.Series("directo", index=idx, dtype="object").where(valor.notna())

    # Residuales (carácter 99): no se clasifican.
    residual = cno.str[:2].eq(CARACTER_RESIDUAL).fillna(False)
    metodo[residual] = "residual"
    valor[residual] = None

    # Vecindad, sólo para lo que no resolvió la tabla.
    pend = metodo.isna() & cno.notna()
    if pend.any():
        claves = zip(cno[pend].str[:2], cno[pend].str[4])
        v = pd.Series([t.bloques.get(k) for k in claves], index=idx[pend], dtype="object")
        v = v.dropna()
        valor[v.index] = v
        metodo[v.index] = "vecindad"

    # Comodines: la tabla (o el bloque vecino) sólo da el gran grupo. Se intenta
    # completar el 2.º dígito con la rama. Lo que viene de la vecindad sigue
    # siendo ad hoc aunque la rama lo resuelva.
    comodin = valor.astype("string").str.startswith("*").fillna(False)
    gran_grupo = valor.where(comodin).astype("string").str[-1]
    if comodin.any():
        claves = zip(gran_grupo[comodin], rama2[comodin].fillna(""))
        res = pd.Series([t.caes.get(k) for k in claves], index=idx[comodin], dtype="object")
        res = res.where(res.isin(t.subgrupos))          # descarta 79 / 89 de la tabla INDEC
        valor[res.index] = res
        desde_tabla = metodo[res.index].eq("directo")
        metodo[res.index] = [
            ("por_actividad" if tab else "vecindad") if pd.notna(r) else "gran_grupo"
            for r, tab in zip(res, desde_tabla)
        ]

    sin_resolver = metodo.isna()
    metodo[sin_resolver & cno.isna()] = "sin_codigo"
    metodo[sin_resolver & cno.notna() & ~cno.isin(t.catalogo)] = "fuera_de_catalogo"
    metodo = metodo.fillna("sin_correspondencia")

    isco_2d = valor.where(valor.isin(t.subgrupos))
    return pd.DataFrame(
        {
            "isco08_2d": isco_2d,
            "isco08_gran_grupo": isco_2d.astype("string").str[0].fillna(gran_grupo),
            "isco08_metodo": metodo,
        },
        index=idx,
    )


def _llenar(out, df, sel, col_cno, col_rama, t):
    cno = normalizar_cno(df.loc[sel, col_cno])
    r = asignar(cno, df.loc[sel, col_rama], t)
    out.loc[sel, "cno01_fuente"] = col_cno
    out.loc[sel, "cno01_5d"] = cno
    out.loc[sel, "cno01_caracter"] = cno.str[:2]
    out.loc[sel, "cno01_caracter_desc"] = cno.str[:2].map(t.desc_caracter)
    out.loc[sel, "cno01_jerarquia"] = cno.str[2]
    out.loc[sel, "cno01_tecnologia"] = cno.str[3]
    out.loc[sel, "cno01_calificacion"] = cno.str[4]
    out.loc[sel, "isco08_2d"] = r["isco08_2d"]
    out.loc[sel, "isco08_2d_desc"] = r["isco08_2d"].map(t.desc_2d)
    out.loc[sel, "isco08_gran_grupo"] = r["isco08_gran_grupo"]
    out.loc[sel, "isco08_gran_grupo_desc"] = r["isco08_gran_grupo"].map(t.desc_gg)
    out.loc[sel, "isco08_metodo"] = r["isco08_metodo"]
    out.loc[sel, "isco08_caso"] = r["isco08_metodo"].map(CASOS)


def cross(df: pd.DataFrame, desocupados: bool = True) -> pd.DataFrame:
    """Agrega las columnas de CIUO-08 a una base individual de la EPH.

    - Ocupados (ESTADO = 1): ocupación principal, PP04D_COD con la rama PP04B_COD.
    - Desocupados (ESTADO = 2) con trabajo anterior: ocupación anterior, PP11D_COD con
      la rama PP11B_COD. Se omite si `desocupados=False` o si la base no trae esas columnas.

    La columna `cno01_fuente` indica de qué variable salió el código. El resto de las
    personas queda con las columnas nuevas vacías. La base puede tener uno o varios
    trimestres y códigos como texto o número; las columnas originales no se modifican.
    """
    faltan = [c for c in (COL_ESTADO, COL_OCUPACION, COL_RAMA) if c not in df.columns]
    if faltan:
        raise KeyError(f"Faltan columnas necesarias: {', '.join(faltan)}")

    t = tablas()
    out = df.copy()
    for c in COLUMNAS_NUEVAS:
        out[c] = pd.Series(pd.NA, index=out.index, dtype="object")

    estado = _limpiar(df[COL_ESTADO])
    ocupados = estado.eq(OCUPADO).fillna(False)
    if ocupados.any():
        _llenar(out, df, ocupados, COL_OCUPACION, COL_RAMA, t)

    if desocupados and {COL_OCUPACION_ANT, COL_RAMA_ANT} <= set(df.columns):
        # Sólo los que declaran una ocupación anterior: el resto nunca trabajó o
        # dejó de trabajar hace más de tres años, y no corresponde clasificarlos.
        con_ant = estado.eq(DESOCUPADO).fillna(False) & _limpiar(df[COL_OCUPACION_ANT]).notna()
        if con_ant.any():
            _llenar(out, df, con_ant, COL_OCUPACION_ANT, COL_RAMA_ANT, t)
    return out
