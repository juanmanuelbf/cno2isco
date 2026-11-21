# Diccionario de la salida

`eph_isco08.csv` tiene una fila por persona y trimestre. Son las bases individuales del INDEC
apiladas, con todas sus variables originales (ver el diseño de registro de la EPH), más las
columnas de abajo. Formato: separador `;`, coma decimal, codificación UTF-8.

Las columnas nuevas están completas para los ocupados (`ESTADO = 1`, ocupación principal) y para
los desocupados con trabajo anterior (`ESTADO = 2` con `PP11D_COD`, ocupación anterior). Para el
resto de las personas quedan vacías. Para tabular una sola población, filtrá por `ESTADO` o por
`cno01_fuente`.

## Columnas nuevas

| Columna | Tipo | Descripción |
|---|---|---|
| `cno01_fuente` | texto | Variable de origen: `PP04D_COD` (ocupados) o `PP11D_COD` (desocupados) |
| `cno01_5d` | texto | Código CNO-2001 a 5 dígitos, con ceros a la izquierda. La variable original queda como vino |
| `cno01_caracter` | texto | Dígitos 1-2: carácter ocupacional |
| `cno01_caracter_desc` | texto | Descripción del carácter ocupacional |
| `cno01_jerarquia` | texto | Dígito 3 (ver tabla abajo) |
| `cno01_tecnologia` | texto | Dígito 4 (ver tabla abajo) |
| `cno01_calificacion` | texto | Dígito 5 (ver tabla abajo) |
| `isco08_2d` | texto | Subgrupo principal CIUO-08 (2 dígitos). Vacío si no se pudo determinar |
| `isco08_2d_desc` | texto | Descripción del subgrupo principal |
| `isco08_gran_grupo` | texto | Gran grupo CIUO-08 (1 dígito). Puede estar aunque `isco08_2d` esté vacío |
| `isco08_gran_grupo_desc` | texto | Descripción del gran grupo |
| `isco08_metodo` | texto | Regla que asignó el código (abajo) |
| `isco08_caso` | texto | `isco08_metodo` agrupado en 5 categorías (abajo) |

Los códigos se guardan como texto para conservar los ceros a la izquierda. Si leés el archivo
con pandas, usá `dtype=str` o al menos `dtype={"isco08_2d": str, "cno01_5d": str}`.

## Valores de `isco08_metodo` e `isco08_caso`

| `isco08_metodo` | `isco08_caso` | Significado |
|---|---|---|
| `directo` | 1. INDEC - directa | Correspondencia de la tabla del INDEC |
| `por_actividad` | 2. INDEC - por actividad | Tabla del INDEC + rama de actividad |
| `vecindad` | 3. Ad hoc - 2 dígitos | Regla de vecindad (código ausente en la tabla) |
| `gran_grupo` | 4. Ad hoc - 1 dígito | Sólo se pudo determinar el gran grupo |
| `residual` | 5. Sin clasificación | Carácter 99 (no especificado) |
| `fuera_de_catalogo` | 5. Sin clasificación | Código inexistente en el CNO-2001 |
| `sin_correspondencia` | 5. Sin clasificación | Código válido no resuelto |
| `sin_codigo` | 5. Sin clasificación | Ocupado sin código de ocupación (no aplica a desocupados) |

Detalle de cada regla en [metodologia.md](metodologia.md).

## Dimensiones del CNO-2001

| Jerarquía (dígito 3) | | Tecnología (dígito 4) | | Calificación (dígito 5) | |
|---|---|---|---|---|---|
| 0 | Dirección | 0 | No aplica (dirección, jefaturas) | 1 | Profesional |
| 1 | Cuenta propia | 1 | Sin operación de maquinaria | 2 | Técnica |
| 2 | Jefes | 2 | Maquinaria y equipos electromecánicos | 3 | Operativa |
| 3 | Trabajadores asalariados | 3 | Sistemas y equipos informatizados | 4 | No calificada |

## Subgrupos principales de la CIUO-08

La lista completa, con sus descripciones, está en
[`src/cno2isco/datos/isco08_2d.csv`](../src/cno2isco/datos/isco08_2d.csv).

## `eph_isco08_cobertura.csv`

Dos filas por trimestre, una por `poblacion` (`ocupados` y `desocupados_ocupacion_anterior`):
`personas` (total de la base), `casos` y `casos_ponderados` de esa población, y para cada método
`casos_<método>` (casos muestrales), `pond_<método>` (suma de `PONDERA`) y `pct_<método>`
(% ponderado). Al final, `pct_isco08_2d` y `pct_isco08_1d_o_mas`.
