# Metodología

`cno2isco` asigna un **subgrupo principal de la CIUO-08** (2 dígitos) a partir del código
CNO-2001 de la ocupación: la ocupación principal de los ocupados (`PP04D_COD`, con la rama
`PP04B_COD`) y la ocupación anterior de los desocupados que tuvieron trabajo (`PP11D_COD`, con la
rama `PP11B_COD`). A los dos se les aplica la misma regla. Este documento explica de
dónde sale cada asignación y por qué se eligieron estas reglas.

## 1. Clasificaciones

**CNO-2001.** El Clasificador Nacional de Ocupaciones del INDEC codifica cada ocupación con
5 dígitos que combinan cuatro dimensiones
([clasificador](https://www.indec.gob.ar/ftp/cuadros/menusuperior/eph/EPHcontinua_CNO2001_reducido_09.pdf)):

| Dígitos | Dimensión | Valores |
|---|---|---|
| 1-2 | Carácter ocupacional | 52 caracteres: qué produce el proceso de trabajo (00 funcionarios del Ejecutivo, 10 gestión administrativa, 72 construcción, 81 producción de software, ...) |
| 3 | Jerarquía | 0 dirección · 1 cuenta propia · 2 jefes · 3 trabajadores asalariados |
| 4 | Tecnología | 1 sin operación de maquinaria · 2 maquinaria electromecánica · 3 sistemas informatizados · 0 no aplica (dirección y jefaturas) |
| 5 | Calificación | 1 profesional · 2 técnica · 3 operativa · 4 no calificada |

El código `05002`, por ejemplo, es *Directivos de pequeñas y microempresas, con calificación
técnica*.

**CIUO-08 (ISCO-08).** La Clasificación Internacional Uniforme de Ocupaciones de la OIT
organiza las ocupaciones por tipo de tareas y nivel de competencias, en 10 grandes grupos
(1 dígito), 43 subgrupos principales (2 dígitos), 130 subgrupos (3) y 436 grupos primarios (4).
`cno2isco` llega a **2 dígitos**, que es la resolución de la tabla oficial.

Las dos clasificaciones parten de lógicas distintas: el CNO describe el proceso de trabajo con
dimensiones independientes, la CIUO agrupa ocupaciones concretas. Por eso la correspondencia no
es exacta y requiere decisiones.

## 2. Fuente: la tabla de correspondencias del INDEC

El punto de partida es la **tabla de correspondencia entre el CNO-2001 y la CIUO-08** que publica
el INDEC junto con los clasificadores de la EPH:

- Archivo original:
  [`CONVERSION_CNO-01_CIUO-08.xls`](https://sitioanterior.indec.gob.ar/ftp/cuadros/menusuperior/eph/CONVERSION_CNO-01_CIUO-08.xls)
- Página donde está publicado:
  [INDEC, Bases de datos → EPH → Clasificadores y códigos](https://sitioanterior.indec.gob.ar/bases-de-datos.asp?solapa=1)
  (*"Tabla de correspondencia Clasificador Nacional de Ocupaciones 2001 (CNO 2001) y
  Clasificación Internacional Uniforme de Ocupaciones 2008 (CIUO-08)"*).

**Contexto.** En 2015 el INDEC adoptó la CIUO-08 como clasificador para el Sistema Estadístico
Nacional, pero en 2018 dejó sin efecto esa decisión y mantuvo el CNO. La
[Resolución INDEC 73/2018](https://www.boletinoficial.gob.ar/detalleAviso/primera/181689/20180416)
señala que el CNO cuenta desde su creación con una tabla de correspondencias a 2 dígitos con la
CIUO, que es la que permite la comparación internacional. Por eso la EPH sigue codificando la
ocupación en CNO-2001 y la CIUO-08 hay que construirla con esa tabla.

La tabla se convirtió a CSV sin cambiar ninguna correspondencia (las únicas correcciones, en la
sección 4, son de etiquetas). Así queda en `src/cno2isco/datos/`:

| Archivo | Contenido | Filas |
|---|---|---:|
| `cno2001_isco08.csv` | Códigos CNO con su CIUO. 569 a 2 dígitos y 25 sólo con el gran grupo (los "comodines", que el INDEC anota como `2(2)`, `7(2)`, etc.) | 594 |
| `caes_isco08.csv` | Tabla auxiliar para los comodines: gran grupo + división de actividad (CAES) → subgrupo de 2 dígitos | 53 |
| `cno2001_catalogo.csv` | Todos los códigos que existen en el CNO-2001, extraídos del clasificador oficial | 984 |
| `isco08_2d.csv`, `isco08_gran_grupo.csv` | Etiquetas de la CIUO-08 | 43 + 10 |
| `cno2001_caracter.csv` | Etiquetas del carácter ocupacional | 53 |

La tabla del INDEC asigna **un único CIUO a cada código CNO** (correspondencia 1:1). Cubre 585 de
los 984 códigos del catálogo; los **399 restantes no tienen correspondencia oficial** y son los que
requieren reglas propias.

## 3. Regla de decisión

Para cada ocupado se aplica, en este orden:

| # | Método (`isco08_metodo`) | Regla | Resultado |
|---|---|---|---|
| 1 | `directo` | El código está en la tabla del INDEC con un CIUO de 2 dígitos | 2 dígitos |
| 2 | `por_actividad` | El código está en la tabla, pero sólo con el gran grupo. El segundo dígito sale de la tabla auxiliar según la división CAES de la rama (`PP04B_COD`) | 2 dígitos |
| 3 | `vecindad` | El código no está en la tabla. Se adopta el CIUO de sus "vecinos" (ver 3.1) | 2 dígitos |
| 4 | `gran_grupo` | Un comodín (por 2 o 3) cuya rama no figura en la tabla auxiliar, o figura con un valor que no existe en la CIUO-08 (79 u 89) | 1 dígito |
| 5 | `residual` | Carácter 99: ocupación no especificada o no clasificable | sin CIUO |
| 5 | `fuera_de_catalogo` | El código no existe en el CNO-2001 (error de codificación) | sin CIUO |
| 5 | `sin_correspondencia` | Código válido que ninguna regla resolvió | sin CIUO |
| 5 | `sin_codigo` | Ocupado sin código de ocupación | sin CIUO |

Los métodos 1 y 2 reproducen la correspondencia oficial; 3 y 4 son decisiones de este proyecto
(**clasificación ad hoc**). La columna `isco08_caso` resume esto en cinco categorías.

### 3.1. Regla de vecindad

Para los códigos que la tabla no contempla, se buscan en la tabla los códigos que comparten
**carácter y calificación** (dejando libres jerarquía y tecnología). Si hay **al menos dos** y
**todos** tienen el mismo CIUO, se le asigna ese CIUO. Si discrepan o hay uno solo, el código queda
sin correspondencia.

Si el valor compartido por los vecinos es un comodín, se completa con la rama igual que en el
método 2, pero el caso se sigue informando como `vecindad` (o `gran_grupo` si la rama no lo
resuelve), porque el origen de la asignación es ad hoc.

De los 399 códigos sin correspondencia oficial, la vecindad resuelve 213 (13 de ellos sólo al
gran grupo, salvo que la rama lo complete) y deja 186 sin resolver.

### 3.2. Por qué carácter y calificación

**Qué dimensiones dejar libres.** Dentro de la propia tabla del INDEC se miraron bloques de
códigos que coinciden en todo menos en una dimensión, y se contó en qué proporción de esos
bloques todos los códigos van al mismo CIUO:

| Dimensión que varía | Bloques donde todos coinciden |
|---|---:|
| Jerarquía | 91,5 % |
| Tecnología | 67,8 % |
| Calificación | 9,9 % |
| Carácter | 0 % |

Jerarquía y tecnología casi no cambian el CIUO, mientras que carácter y calificación lo
determinan. Tiene sentido con la lógica de la CIUO-08, que agrupa por tipo de tarea (carácter) y
nivel de competencias (calificación): un administrativo es administrativo trabaje o no con
computadora, y sea o no jefe de sección.

**Cuán estricta hacer la regla.** Se probaron dos variantes prediciendo, para cada código que
*sí* está en la tabla, su CIUO a partir de los demás (validación dentro de la tabla):

| Regla | Predicción acertada |
|---|---:|
| Varía sólo la jerarquía | 91,5 % |
| Varían jerarquía y tecnología, con mínimo 2 vecinos | 96,2 % |

Se eligió la segunda: acierta más y su costo en casos sin clasificar es chico.

| Regla | % con CIUO a 2 dígitos | % sin clasificar |
|---|---:|---:|
| Varía sólo la jerarquía | 93,42 | 3,82 |
| **Varían jerarquía y tecnología, con mínimo 2 vecinos** (la elegida) | **95,72** | **1,33** |

*Período 2017T1-2026T1, ocupados, casos ponderados con `PONDERA`.*

La regla elegida no sólo acierta más en la validación: como agrupa más códigos por bloque, también
clasifica más casos.

### 3.3. Rama de actividad

La tabla auxiliar usa la **división** CAES (2 dígitos). En los microdatos `PP04B_COD` aparece:

- a 4 dígitos (`4803` → división 48);
- a 3 dígitos cuando perdió el cero inicial (`101` → `0101` → división 01);
- a 1 o 2 dígitos cuando sólo se conoce la división (`48` → 48; `1` → 01).

### 3.4. Normalización del código CNO

`PP04D_COD` pierde los ceros a la izquierda al exportarse (`5002` en lugar de `05002`). Se
completa a 5 dígitos antes de cualquier búsqueda. El código original queda intacto en la base.

## 4. Correcciones respecto de los archivos fuente

- **Etiquetas de la CIUO.** La tabla del INDEC no trae los subgrupos 63 (*Trabajadores
  agropecuarios, pescadores, cazadores y recolectores de subsistencia*) y 82 (*Ensambladores*),
  aunque el 82 aparece como destino en la tabla auxiliar. Se agregaron con la denominación de la
  CIUO-08. Se corrigieron dos erratas ("elecrotecnología", "administración publica").
- **Valores 79 y 89 de la tabla auxiliar.** No existen en la CIUO-08 (12 de las 53 reglas). No se
  usan: esos casos quedan con el gran grupo.
- **Descripciones de los códigos CNO.** La descripción a 5 dígitos que acompaña a la tabla del
  INDEC está desalineada en algunos bloques (por ejemplo, en el carácter 81 aparece corrida un
  nivel de jerarquía). No se incluye. Las etiquetas salen de los dígitos del código, que sí son
  correctos (`cno01_caracter_desc` y las dimensiones en `docs/diccionario.md`).
- **9 códigos de la tabla que no están en el catálogo** (`34112`, `34122`, `51201`, `55113`,
  `56111`, `56114`, `60114`, `72114`, `80111`). Se respeta la correspondencia del INDEC.

## 5. Resultados de referencia

Corrida sobre 2017T1-2026T1 (37 trimestres, 791.358 ocupados en la muestra). Porcentajes sobre
ocupados, ponderados con `PONDERA`:

| Caso | % casos ponderados | Casos |
|---|---:|---:|
| **Clasificación INDEC** | **91,77** | **736.210** |
| &nbsp;&nbsp;Directa | 87,23 | 703.970 |
| &nbsp;&nbsp;Por actividad | 4,55 | 32.240 |
| **Clasificación ad hoc** | **6,90** | **47.193** |
| &nbsp;&nbsp;2 dígitos (vecindad) | 3,94 | 27.350 |
| &nbsp;&nbsp;1 dígito (gran grupo) | 2,95 | 19.843 |
| **Sin clasificación** | **1,33** | **7.955** |
| &nbsp;&nbsp;Residual (carácter 99) | 0,74 | 3.502 |
| &nbsp;&nbsp;Fuera del catálogo | 0,17 | 1.414 |
| &nbsp;&nbsp;Sin correspondencia | 0,42 | 3.039 |
| **CIUO-08 a 2 dígitos** | **95,72** | |
| **CIUO-08 al menos a 1 dígito** | **98,67** | |

Por trimestre, la cobertura a 2 dígitos va de 94,86 % (2024T4) a 96,46 % (2017T3).

**Desocupados con ocupación anterior** (45.517 casos en la muestra): 95,78 % queda con CIUO a
2 dígitos y 98,64 % al menos a 1 dígito.

El detalle por trimestre y población está en el archivo `eph_isco08_cobertura.csv` que genera
cada corrida.

## 6. Otras propuestas

Chávez Molina, Bernasconi y Rodríguez de la Fuente (2020) también parten de la tabla del INDEC,
con modificaciones puntuales y soluciones propias para los códigos sin clasificar, y publican la
sintaxis para SPSS, Stata y R ([enlace](https://www.aacademica.org/joserodriguez/74)). Las reglas
de `cno2isco` para los códigos sin correspondencia son independientes de esa propuesta.

## Referencias

- INDEC. *Clasificador Nacional de Ocupaciones (CNO-2001)*. Versión para la EPH continua.
  [PDF](https://sitioanterior.indec.gob.ar/ftp/cuadros/menusuperior/eph/EPHcontinua_CNO2001_reducido_09.pdf).
- INDEC. *Tabla de correspondencia CNO-2001 – CIUO-08.*
  [XLS](https://sitioanterior.indec.gob.ar/ftp/cuadros/menusuperior/eph/CONVERSION_CNO-01_CIUO-08.xls).
- INDEC (2018). *Resolución 73/2018.* Boletín Oficial, 16/04/2018.
- Chávez Molina, E., Bernasconi, F. y Rodríguez de la Fuente, J. J. (2020). *Propuesta de
  correspondencias entre CNO y CIUO. Sintaxis para SPSS, Stata y R.* IIGG-UBA.
- OIT (2012). *Clasificación Internacional Uniforme de Ocupaciones, CIUO-08.* Ginebra: OIT.
