"""Comando de terminal: cno2isco [CARPETA]"""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path

from . import __version__
from . import consola as c
from .cobertura import Cobertura
from .correspondencia import COLUMNAS_NUEVAS, cross, tablas
from .lectura import ErrorEntrada, buscar, leer_base, periodos_faltantes

SALIDA = "eph_isco08.csv"
SALIDA_COBERTURA = "eph_isco08_cobertura.csv"
PASOS = 4


def _argumentos(argv):
    p = argparse.ArgumentParser(
        prog="cno2isco",
        description="Agrega la ocupación en CIUO-08 (ISCO-08) a los microdatos individuales "
                    "de la EPH-INDEC, a partir del código CNO-2001.",
    )
    p.add_argument("carpeta", nargs="?", default="microdatos",
                   help="carpeta con los .zip (o .txt) descargados del INDEC "
                        "(por defecto: ./microdatos)")
    p.add_argument("--version", action="version", version=f"cno2isco {__version__}")
    return p.parse_args(argv)


def _buscar(carpeta: Path):
    c.paso(1, PASOS, f"Buscando microdatos en {carpeta.resolve()}")
    bases, omitidos, duplicados = buscar(carpeta)

    for b in bases:
        c.linea(f"{b.periodo}   {b.nombre}")
    for o in omitidos:
        c.linea(f"--       {o.nombre}  (omitido: {o.motivo})")
    for nuevo, previo in duplicados:
        c.aviso(f"{nuevo.periodo} aparece dos veces: uso {previo.nombre} e ignoro {nuevo.nombre}")

    if not bases:
        raise ErrorEntrada(
            f"No encontré bases individuales de la EPH en {carpeta.resolve()}",
            "Poné ahí los .zip descargados del INDEC (formato txt), sin descomprimir, "
            "y volvé a correr el comando.",
        )

    periodos = [b.periodo for b in bases]
    print()
    c.ok(f"{len(bases)} trimestre{'s' if len(bases) > 1 else ''}: {periodos[0]} a {periodos[-1]}")
    faltan = periodos_faltantes(periodos)
    if faltan:
        c.aviso(f"faltan {len(faltan)} trimestre(s) en el medio: {', '.join(faltan)}")
    return bases


def _procesar(bases, destino: Path, cobertura: Cobertura):
    c.paso(3, PASOS, "Aplicando la correspondencia")

    originales = []
    for b in bases:
        for col in b.columnas:
            if col and col not in originales:
                originales.append(col)
    columnas = originales + COLUMNAS_NUEVAS

    filas = 0
    with open(destino, "w", encoding="utf-8-sig", newline="") as fh:
        for i, b in enumerate(bases):
            try:
                df = leer_base(b)
                periodos = (df["ANO4"].astype(str) + "T" + df["TRIMESTRE"].astype(str)).unique()
                if len(periodos) > 1:
                    c.aviso(f"{b.nombre} trae más de un período: {', '.join(map(str, periodos))}")
                out = cross(df).reindex(columns=columnas)
                out.to_csv(fh, sep=";", index=False, header=(i == 0), lineterminator="\r\n")
            except ErrorEntrada:
                raise
            except Exception as e:
                raise ErrorEntrada(f"Falló el procesamiento de {b.nombre} ({b.periodo})",
                                   f"{type(e).__name__}: {e}") from e
            f = cobertura.agregar(b.periodo, out)
            o, d = f["ocupados"], f["desocupados_ocupacion_anterior"]
            filas += len(out)
            c.linea(f"{b.periodo}   {c.miles(o['personas']):>7} personas   "
                    f"{c.miles(o['casos']):>7} ocupados   {c.miles(d['casos']):>6} desocupados   "
                    f"CIUO a 2 dígitos: {c.pct(cobertura.pct_2d(o), 1):>7}")
    return filas, len(columnas)


def ejecutar(carpeta: Path):
    reloj = c.Reloj()
    c.titulo(f"cno2isco {__version__}  -  CNO-2001 -> CIUO-08 (ISCO-08) para la EPH")

    bases = _buscar(carpeta)

    c.paso(2, PASOS, "Cargando la tabla de correspondencia")
    t = tablas()
    c.ok(f"{len(t.directo)} códigos CNO en la tabla del INDEC, {len(t.caes)} reglas por rama, "
         f"{len(t.bloques)} bloques de vecindad")

    salida = Path.cwd() / SALIDA
    parcial = salida.with_name(salida.name + ".parcial")
    if salida.exists():
        c.aviso(f"{SALIDA} ya existe en esta carpeta: se va a reemplazar al terminar")

    cobertura = Cobertura()
    try:
        filas, ncols = _procesar(bases, parcial, cobertura)
        c.paso(4, PASOS, "Guardando")
        try:
            os.replace(parcial, salida)
            cobertura.tabla().to_csv(Path.cwd() / SALIDA_COBERTURA, sep=";", decimal=",",
                                     index=False, encoding="utf-8-sig")
        except PermissionError as e:
            raise ErrorEntrada(f"No pude escribir {Path(e.filename or SALIDA).name}",
                               "¿Está abierto en Excel u otro programa? Cerralo y volvé a correr.") from e
    finally:
        if parcial.exists():
            parcial.unlink()

    c.ok(f"{salida}  ({c.miles(filas)} filas x {ncols} columnas, {c.tamano(salida.stat().st_size)})")
    c.ok(f"{Path.cwd() / SALIDA_COBERTURA}  (cobertura por trimestre)")
    cobertura.imprimir()
    print(f"\nListo en {reloj}.\n")


def main(argv=None):
    c.preparar()
    args = _argumentos(argv)
    try:
        ejecutar(Path(args.carpeta))
    except ErrorEntrada as e:
        mensaje, *detalle = e.args
        c.error(mensaje, detalle[0] if detalle else None)
        return 1
    except KeyboardInterrupt:
        c.error("Cancelado por el usuario. No se generó ningún archivo.")
        return 130
    except Exception as e:  # algo que no anticipamos: mostrar todo para poder reportarlo
        c.error(f"Error inesperado: {type(e).__name__}: {e}",
                "Si no se entiende la causa, abrí un issue en "
                "https://github.com/juanmanuelbf/cno2isco/issues con este mensaje:\n\n"
                + traceback.format_exc())
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
