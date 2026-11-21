# Limitaciones

Lo que `cno2isco` no resuelve, o resuelve con supuestos que conviene tener presentes al usar
los resultados.

## Sobre la correspondencia

**1. Correspondencia 1:1 entre clasificaciones que no son equivalentes.** La tabla del INDEC
asigna un único subgrupo CIUO a cada código CNO. En la práctica, un mismo código CNO puede
corresponder a ocupaciones que la CIUO separa en subgrupos distintos (y al revés). El resultado
describe bien la estructura agregada, pero no cada caso individual.

**2. Resolución a 2 dígitos.** Todos los ocupados de un subgrupo comparten código, aunque
adentro haya ocupaciones muy distintas (en el subgrupo 52, *Vendedores*, conviven vendedores de
comercio y vendedores telefónicos). Quien necesite 3 o 4 dígitos tiene que hacer supuestos
adicionales sobre la composición del empleo dentro de cada subgrupo.

**3. Las reglas ad hoc son inferencias.** La regla de vecindad reproduce el 96,2 % de las
asignaciones del INDEC cuando se prueba sobre la propia tabla, pero se aplica justamente a
códigos que el INDEC no clasificó, que pueden no comportarse igual. Afecta al 3,94 % de los
ocupados (ponderado). La columna `isco08_metodo` permite excluir estos casos o hacer análisis de
sensibilidad.

**4. Casos que quedan en el gran grupo.** Un 2,95 % de los ocupados queda sólo con 1 dígito,
en su gran mayoría de la producción industrial y artesanal (carácter 80) y el resto de
investigación (42) y asesoría y consultoría (43). Son ocupaciones para las que la tabla del INDEC
depende de la rama, y la rama no siempre está en la tabla auxiliar. Si se trabaja a 2 dígitos, estos casos quedan afuera.

**5. Dependencia de la rama de actividad.** Para los comodines, el subgrupo depende de que la
rama esté bien codificada. Un error en `PP04B_COD` se traslada a la ocupación.

**6. Casos sin clasificar.** El 1,33 % restante no tiene CIUO: residuales (carácter 99),
códigos inexistentes en el CNO-2001 y códigos válidos sin vecinos que coincidan. No están
distribuidos al azar entre ocupaciones, así que excluirlos puede sesgar levemente la
estructura. Su peso es chico, pero conviene reportarlo.

## Sobre los datos

**7. Qué ocupación se traduce.** Para los ocupados, sólo la ocupación principal (`PP04D_COD`); la
EPH no codifica las ocupaciones secundarias. Para los desocupados, la del último trabajo
(`PP11D_COD`), que la EPH releva sólo si terminó en los últimos tres años: los desocupados sin
trabajo anterior o que dejaron de trabajar antes quedan sin ocupación. Ocupados y desocupados
comparten columnas en la salida; `cno01_fuente` indica de cuál viene cada caso.

**8. Comparabilidad en el tiempo.** El clasificador y la tabla son los mismos para toda la
serie, pero la muestra de la EPH no: 2020T2 y 2020T3 se relevaron por teléfono, con muestra
reducida. Además, la calidad de la codificación de la ocupación puede variar entre trimestres
(la cobertura a 2 dígitos va de 94,86 % a 96,46 % según el trimestre).

**9. La CIUO-08 a 2 dígitos no es la que reporta el INDEC.** Las publicaciones oficiales usan el
CNO. Los resultados de `cno2isco` son una elaboración propia sobre los microdatos y deben
presentarse como tal.

## Sobre el formato

**10. Corrección del decimal.** En los trimestres que el INDEC publicó con punto decimal, se
convierte a coma todo campo sin comillas que tenga la forma `123.45`. No se encontraron campos
que tengan esa forma y no sean números, pero la regla es general.

**11. Lo que no se corrige.** Las entidades HTML de los campos de texto (`A&ntilde;elo`) y las
fechas de nacimiento (`CH05`) con año de dos dígitos en algunos trimestres quedan como vienen.
