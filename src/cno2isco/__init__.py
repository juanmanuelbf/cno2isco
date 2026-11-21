"""cno2isco: CNO-2001 -> CIUO-08 (ISCO-08) para los microdatos de la EPH-INDEC.

Uso desde Python:

    import cno2isco
    df = cno2isco.cross(df)      # agrega las columnas cno01_* e isco08_*
"""

__version__ = "0.1.0"

from .correspondencia import COLUMNAS_NUEVAS, cross  # noqa: E402

__all__ = ["cross", "COLUMNAS_NUEVAS", "__version__"]
