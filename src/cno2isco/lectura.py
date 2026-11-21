"""Búsqueda y lectura de los microdatos de la EPH tal como los publica el INDEC.

No depende del nombre de los archivos: recorre la carpeta (y los .zip que haya
adentro), mira el encabezado de cada .txt/.csv y se queda con las bases
individuales. El trimestre sale de ANO4 y TRIMESTRE, dentro del archivo.

Tolera los defectos de formato conocidos de las bases del INDEC:
encabezado entrecomillado, `;` sobrante al final de cada línea, saltos de línea
LF o CRLF, el literal NA como faltante y punto como separador decimal en
algunos trimestres (se convierte a coma, como en el resto de la serie).
"""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

EXTENSIONES = {".txt", ".csv"}
ID_PERSONA = ["CODUSU", "NRO_HOGAR", "COMPONENTE"]
MARCA_EPH = {"CODUSU", "ANO4", "TRIMESTRE"}
NECESARIAS = ["ANO4", "TRIMESTRE", "ESTADO", "PONDERA", "PP04D_COD", "PP04B_COD"]

# Un campo sin comillas de la forma 123.45 entre separadores.
_DECIMAL_PUNTO = re.compile(r"(?<=[;\n])(-?\d+)\.(\d+)(?=;|\r|\n|$)")


class ErrorEntrada(Exception):
    """Problema con un archivo de entrada, con un mensaje pensado para el usuario."""


@dataclass
class Fuente:
    ruta: Path                    # archivo en disco (.txt/.csv o .zip)
    miembro: str | None = None    # nombre dentro del .zip, si corresponde
    columnas: list = field(default_factory=list)
    periodo: str = ""             # p. ej. "2025T1"

    @property
    def nombre(self) -> str:
        return f"{self.ruta.name} > {self.miembro}" if self.miembro else self.ruta.name

    def leer_bytes(self, n: int = -1) -> bytes:
        """Lee el archivo completo, o sólo los primeros `n` bytes."""
        if self.miembro is None:
            with open(self.ruta, "rb") as fh:
                return fh.read(n)
        with zipfile.ZipFile(self.ruta) as z, z.open(self.miembro) as fh:
            return fh.read(n)


@dataclass
class Omitido:
    nombre: str
    motivo: str


# --------------------------------------------------------------------------- #
# Decodificación y parseo
# --------------------------------------------------------------------------- #
def _decodificar(datos: bytes) -> str:
    if datos.startswith(b"\xef\xbb\xbf"):
        return datos[3:].decode("utf-8")
    try:
        return datos.decode("utf-8")
    except UnicodeDecodeError:
        return datos.decode("latin-1")


def _primera_linea(datos: bytes) -> str:
    return _decodificar(datos.split(b"\n", 1)[0][:20000]).strip("\r\n")


def _separador(linea: str) -> str:
    return ";" if linea.count(";") >= linea.count(",") else ","


def _columnas(linea: str) -> list:
    return [c.strip().strip('"').strip() for c in linea.split(_separador(linea))]


def leer_base(fuente: Fuente) -> pd.DataFrame:
    """Lee una base individual completa, todo como texto, y corrige el formato."""
    texto = _decodificar(fuente.leer_bytes())
    sep = _separador(texto.split("\n", 1)[0])
    if sep == ";":
        texto = _DECIMAL_PUNTO.sub(r"\1,\2", texto)
    df = pd.read_csv(
        io.StringIO(texto),
        sep=sep,
        dtype=str,
        keep_default_na=False,
        na_values=["", "NA"],
        low_memory=False,
    )
    df.columns = [str(c).strip().strip('"').strip() for c in df.columns]
    # Columna fantasma por un `;` al final de cada línea.
    vacias = [c for c in df.columns if (c == "" or c.startswith("Unnamed:")) and df[c].isna().all()]
    return df.drop(columns=vacias)


# --------------------------------------------------------------------------- #
# Búsqueda
# --------------------------------------------------------------------------- #
def _candidatos(carpeta: Path):
    for ruta in sorted(p for p in carpeta.rglob("*") if p.is_file()):
        ext = ruta.suffix.lower()
        if ext == ".zip":
            try:
                with zipfile.ZipFile(ruta) as z:
                    miembros = [m for m in z.namelist() if not m.endswith("/")]
            except zipfile.BadZipFile:
                yield Omitido(ruta.name, "el .zip está dañado o incompleto; volvé a descargarlo")
                continue
            utiles = [m for m in miembros if Path(m).suffix.lower() in EXTENSIONES]
            if not utiles:
                tipos = sorted({Path(m).suffix.lower() or "sin extensión" for m in miembros})
                yield Omitido(ruta.name, f"no tiene .txt adentro ({', '.join(tipos)}); "
                                         "bajá la versión en formato txt")
            for m in utiles:
                yield Fuente(ruta, m)
        elif ext in EXTENSIONES:
            yield Fuente(ruta)
        elif ext in {".xls", ".xlsx"}:
            yield Omitido(ruta.name, "formato Excel no soportado; bajá la versión en formato txt")


def _periodo(fuente: Fuente, datos: bytes) -> str:
    """Lee ANO4 y TRIMESTRE de las primeras filas de datos."""
    lineas = _decodificar(datos).splitlines()[:-1] or _decodificar(datos).splitlines()
    cab = _columnas(lineas[0])
    sep = _separador(lineas[0])
    ia, it = cab.index("ANO4"), cab.index("TRIMESTRE")
    for linea in lineas[1:]:
        if linea.strip():
            campos = [c.strip().strip('"') for c in linea.split(sep)]
            ano, tri = campos[ia], campos[it]
            if not (ano.isdigit() and len(ano) == 4 and tri in {"1", "2", "3", "4"}):
                raise ErrorEntrada(f"{fuente.nombre}: ANO4={ano!r} y TRIMESTRE={tri!r} "
                                   "no parecen un año y un trimestre válidos")
            return f"{ano}T{tri}"
    raise ErrorEntrada(f"{fuente.nombre}: el archivo tiene encabezado pero no tiene filas")


def buscar(carpeta: Path):
    """Devuelve (bases individuales ordenadas por período, omitidos, duplicados)."""
    if not carpeta.exists():
        raise ErrorEntrada(f"No existe la carpeta {carpeta.resolve()}",
                           "Creala y poné adentro los .zip descargados del INDEC, o indicá "
                           "otra carpeta: cno2isco RUTA/A/LA/CARPETA")
    if not carpeta.is_dir():
        raise ErrorEntrada(f"{carpeta.resolve()} no es una carpeta")

    bases, omitidos, duplicados = {}, [], []
    for c in _candidatos(carpeta):
        if isinstance(c, Omitido):
            omitidos.append(c)
            continue
        try:
            datos = c.leer_bytes(200_000)
        except (OSError, zipfile.BadZipFile, KeyError) as e:
            raise ErrorEntrada(f"No pude abrir {c.nombre}: {e}") from e
        cols = _columnas(_primera_linea(datos))
        if not MARCA_EPH <= set(cols):
            omitidos.append(Omitido(c.nombre, "no es una base de la EPH"))
            continue
        if "COMPONENTE" not in cols:
            omitidos.append(Omitido(c.nombre, "base de hogares (no se usa)"))
            continue
        faltan = [n for n in NECESARIAS if n not in cols]
        if faltan:
            raise ErrorEntrada(f"{c.nombre} es una base individual pero le faltan columnas "
                               f"necesarias: {', '.join(faltan)}")
        c.columnas = cols
        c.periodo = _periodo(c, datos)
        if c.periodo in bases:
            duplicados.append((c, bases[c.periodo]))
            continue
        bases[c.periodo] = c

    ordenadas = sorted(bases.values(), key=lambda f: (int(f.periodo[:4]), int(f.periodo[-1])))
    return ordenadas, omitidos, duplicados


def periodos_faltantes(periodos: list) -> list:
    """Trimestres que faltan entre el primero y el último encontrados."""
    if not periodos:
        return []
    clave = [int(p[:4]) * 4 + int(p[-1]) - 1 for p in periodos]
    presentes = set(clave)
    return [f"{k // 4}T{k % 4 + 1}" for k in range(min(clave), max(clave) + 1) if k not in presentes]
