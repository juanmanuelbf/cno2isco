"""Resumen de cobertura: qué parte de los ocupados (y de los desocupados con
ocupación anterior) quedó clasificada y cómo."""

from __future__ import annotations

import pandas as pd

from . import consola as c
from .correspondencia import CASOS

METODOS = list(CASOS)
ANCHO_TABLA = 68

GRUPOS = [
    ("Clasificación INDEC", [("directa", "directo"), ("por actividad (rama)", "por_actividad")]),
    ("Clasificación ad hoc", [("2 dígitos (vecindad)", "vecindad"), ("sólo gran grupo, 1 dígito", "gran_grupo")]),
    ("Sin clasificación", [("residual (carácter 99)", "residual"),
                           ("código fuera del catálogo CNO-2001", "fuera_de_catalogo"),
                           ("sin correspondencia", "sin_correspondencia"),
                           ("sin código de ocupación", "sin_codigo")]),
]


def _numero(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie.astype("string").str.replace(",", ".", regex=False), errors="coerce").fillna(0)


POBLACIONES = {"PP04D_COD": "ocupados", "PP11D_COD": "desocupados_ocupacion_anterior"}
DOS_DIGITOS = ("directo", "por_actividad", "vecindad")


class Cobertura:
    def __init__(self):
        self.filas = []

    def agregar(self, periodo: str, df: pd.DataFrame) -> dict:
        """Registra un trimestre ya procesado. Devuelve la fila de los ocupados."""
        filas = {}
        for fuente, poblacion in POBLACIONES.items():
            sub = df[df["cno01_fuente"].eq(fuente).fillna(False)]
            peso = _numero(sub["PONDERA"])
            fila = {"periodo": periodo, "poblacion": poblacion, "personas": len(df),
                    "casos": len(sub), "casos_ponderados": peso.sum()}
            for m in METODOS:
                es = sub["isco08_metodo"].eq(m)
                fila[f"casos_{m}"] = int(es.sum())
                fila[f"pond_{m}"] = peso[es].sum()
            self.filas.append(fila)
            filas[poblacion] = fila
        return filas

    def tabla(self) -> pd.DataFrame:
        """Una fila por trimestre y población: casos y % ponderado de cada método."""
        t = pd.DataFrame(self.filas)
        if t.empty:
            return t
        tot = t["casos_ponderados"].where(t["casos_ponderados"] > 0)
        for m in METODOS:
            t[f"pct_{m}"] = 100 * t[f"pond_{m}"] / tot
        t["pct_isco08_2d"] = t[[f"pct_{m}" for m in DOS_DIGITOS]].sum(axis=1, min_count=1)
        t["pct_isco08_1d_o_mas"] = t["pct_isco08_2d"] + t["pct_gran_grupo"]
        return t.round(4)

    @staticmethod
    def pct_2d(fila: dict) -> float:
        tot = fila["casos_ponderados"]
        return 100 * sum(fila[f"pond_{m}"] for m in DOS_DIGITOS) / tot if tot else 0.0

    def imprimir(self):
        todas = pd.DataFrame(self.filas)
        if todas.empty:
            return
        t = todas[todas["poblacion"] == "ocupados"].reset_index(drop=True)
        tot = t["casos_ponderados"].sum()
        p = {m: 100 * t[f"pond_{m}"].sum() / tot for m in METODOS}
        n = {m: int(t[f"casos_{m}"].sum()) for m in METODOS}
        desde, hasta = t["periodo"].iloc[0], t["periodo"].iloc[-1]

        c.titulo(f"Cobertura {desde} - {hasta}  (ocupados, % de casos ponderados)")
        print(f"  {'':44}{'% pond.':>12}{'casos':>12}")
        for grupo, items in GRUPOS:
            sub_p = sum(p[m] for _, m in items)
            sub_n = sum(n[m] for _, m in items)
            print(f"  {grupo:<44}{c.pct(sub_p):>12}{c.miles(sub_n):>12}")
            for etiqueta, m in items:
                if m == "sin_codigo" and n[m] == 0:
                    continue    # sólo se muestra si aparece
                print(f"      {etiqueta:<40}{c.pct(p[m]):>12}{c.miles(n[m]):>12}")
        print("  " + "-" * ANCHO_TABLA)
        dos = p["directo"] + p["por_actividad"] + p["vecindad"]
        print(f"  {'CIUO-08 a 2 dígitos':<44}{c.pct(dos):>12}")
        print(f"  {'CIUO-08 al menos a 1 dígito (gran grupo)':<44}{c.pct(dos + p['gran_grupo']):>12}")
        print("  " + "-" * ANCHO_TABLA)
        q = t.assign(x=100 * t[[f"pond_{m}" for m in DOS_DIGITOS]].sum(axis=1)
                     / t["casos_ponderados"])
        lo, hi = q.loc[q["x"].idxmin()], q.loc[q["x"].idxmax()]
        print(f"  Por trimestre, a 2 dígitos: mínimo {c.pct(lo['x'])} ({lo['periodo']}), "
              f"máximo {c.pct(hi['x'])} ({hi['periodo']})")

        d = todas[todas["poblacion"] != "ocupados"]
        if d["casos"].sum():
            tot_d = d["casos_ponderados"].sum()
            p2 = 100 * sum(d[f"pond_{m}"].sum() for m in DOS_DIGITOS) / tot_d
            p1 = p2 + 100 * d["pond_gran_grupo"].sum() / tot_d
            print()
            print(f"  Desocupados con ocupación anterior (PP11D_COD): {c.miles(d['casos'].sum())} casos")
            print(f"      CIUO-08 a 2 dígitos {c.pct(p2)}, al menos a 1 dígito {c.pct(p1)}")
