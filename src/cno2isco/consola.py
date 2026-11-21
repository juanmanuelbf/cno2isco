"""Salida prolija por terminal, sólo con caracteres que cualquier consola muestra."""

from __future__ import annotations

import sys
import time

ANCHO = 72


def preparar():
    # En consolas de Windows con codificación vieja, que un caracter raro no corte el programa.
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass


def titulo(texto: str):
    print()
    print("=" * ANCHO)
    print(f"  {texto}")
    print("=" * ANCHO)


def paso(n: int, total: int, texto: str):
    print(f"\n[{n}/{total}] {texto}")


def linea(texto: str = "", sangria: int = 6):
    print(" " * sangria + texto)


def ok(texto: str):
    linea(f"[ok] {texto}")


def aviso(texto: str):
    linea(f"[!]  {texto}")


def error(texto: str, detalle: str | None = None):
    print(file=sys.stderr)
    print("-" * ANCHO, file=sys.stderr)
    print(f"  [ERROR] {texto}", file=sys.stderr)
    if detalle:
        for d in detalle.splitlines():
            print(f"          {d}", file=sys.stderr)
    print("-" * ANCHO, file=sys.stderr)


def miles(n: float) -> str:
    return f"{n:,.0f}".replace(",", ".")


def pct(x: float, decimales: int = 2) -> str:
    return f"{x:.{decimales}f}".replace(".", ",") + " %"


def tamano(bytes_: int) -> str:
    for unidad in ("B", "KB", "MB", "GB"):
        if bytes_ < 1024 or unidad == "GB":
            return f"{bytes_:.0f} {unidad}" if unidad in ("B", "KB") else f"{bytes_:.1f} {unidad}".replace(".", ",")
        bytes_ /= 1024


class Reloj:
    def __init__(self):
        self.t0 = time.perf_counter()

    def __str__(self):
        s = int(time.perf_counter() - self.t0)
        return f"{s // 60} min {s % 60:02d} s" if s >= 60 else f"{s} s"
