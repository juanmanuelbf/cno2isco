"""Pruebas mínimas. Correr con:  pytest"""

import zipfile

import pandas as pd

import cno2isco
from cno2isco.cli import main
from cno2isco.correspondencia import tablas


def _caso(cno, rama="", estado="1"):
    df = pd.DataFrame({"ESTADO": [estado], "PP04D_COD": [cno], "PP04B_COD": [rama]})
    return cno2isco.cross(df).iloc[0]


def test_directo_y_ceros_a_la_izquierda():
    r = _caso("5002")                       # 05002 -> 14
    assert (r.cno01_5d, r.isco08_2d, r.isco08_metodo) == ("05002", "14", "directo")


def test_por_actividad_y_gran_grupo():
    r = _caso("42111", rama="7200")         # gran grupo 2 + CAES 72 -> 21
    assert (r.isco08_2d, r.isco08_metodo) == ("21", "por_actividad")
    r = _caso("42111", rama="72")           # rama sólo a 2 dígitos
    assert r.isco08_2d == "21"
    r = _caso("42111", rama="9999")         # rama sin regla -> sólo gran grupo
    assert pd.isna(r.isco08_2d)
    assert (r.isco08_gran_grupo, r.isco08_metodo) == ("2", "gran_grupo")


def test_vecindad():
    t = tablas()
    en_tabla = set(t.directo)
    cod = next(c for c in sorted(t.catalogo)
               if c not in en_tabla and not t.bloques.get((c[:2], c[4]), "*").startswith("*"))
    r = _caso(cod)
    assert r.isco08_metodo == "vecindad" and r.isco08_2d == t.bloques[(cod[:2], cod[4])]


def test_sin_clasificacion_y_no_ocupados():
    assert _caso("99999").isco08_metodo == "residual"
    assert _caso("30319").isco08_metodo == "fuera_de_catalogo"
    assert _caso("").isco08_metodo == "sin_codigo"
    assert pd.isna(_caso("10111", estado="3").isco08_metodo)


def test_desocupados_ocupacion_anterior():
    df = pd.DataFrame({
        "ESTADO":    ["1",     "2",     "2",  "3"],
        "PP04D_COD": ["10111", "",      "",   ""],
        "PP04B_COD": ["4803",  "",      "",   ""],
        "PP11D_COD": ["",      "5002",  "",   "10111"],
        "PP11B_COD": ["0",     "4803",  "0",  "4803"],
    })
    out = cno2isco.cross(df)
    assert out["cno01_fuente"].tolist()[:2] == ["PP04D_COD", "PP11D_COD"]
    assert out["isco08_2d"].tolist()[:2] == ["24", "14"]
    assert out.iloc[2:]["isco08_metodo"].isna().all()   # sin ocupación anterior / inactivo
    assert cno2isco.cross(df, desocupados=False)["isco08_metodo"].notna().sum() == 1


ENCABEZADO = ["CODUSU", "ANO4", "TRIMESTRE", "NRO_HOGAR", "COMPONENTE", "ESTADO",
              "PONDERA", "PP04B_COD", "PP04D_COD", "PP09A_ESP", "IPCF"]


def _base(ano, tri, comillas=False, punto=False, na=False, sobrante=False, eol="\r\n"):
    cab = [f'"{c}"' for c in ENCABEZADO] if comillas else ENCABEZADO
    dec = "1500.50" if punto else "1500,50"
    filas = [
        ["TQRMNOAAAHKLMNOP", ano, tri, "1", "1", "1", "250", "4803", "10111", '"A&ntilde;elo"', dec],
        ["TQRMNOAAAHKLMNOP", ano, tri, "1", "2", "3", "250", "NA" if na else "", "", "", dec],
    ]
    fin = ";" if sobrante else ""
    return eol.join(";".join(f) + fin for f in [cab] + filas) + eol


def test_corrida_completa(tmp_path, monkeypatch):
    entrada = tmp_path / "microdatos"
    entrada.mkdir()
    # Un zip con nombre raro, encabezado entrecomillado, decimal con punto, NA y ; final.
    with zipfile.ZipFile(entrada / "EPH_usu_1er_Trim_2021_txt.zip", "w") as z:
        z.writestr("Usu_Individual_T121.txt.txt",
                   _base("2021", "1", comillas=True, punto=True, na=True, sobrante=True, eol="\n").encode("latin-1"))
        z.writestr("usu_hogar_T121.txt", "CODUSU;ANO4;TRIMESTRE;NRO_HOGAR\r\nX;2021;1;1\r\n")
    # Un .txt suelto, prolijo.
    (entrada / "cualquier_nombre.txt").write_bytes(_base("2020", "4").encode("latin-1"))
    (entrada / "notas.xlsx").write_bytes(b"")

    monkeypatch.chdir(tmp_path)
    assert main([str(entrada)]) == 0

    out = pd.read_csv(tmp_path / "eph_isco08.csv", sep=";", dtype=str, encoding="utf-8-sig")
    assert len(out) == 4
    assert list(out["ANO4"] + "T" + out["TRIMESTRE"]) == ["2020T4", "2020T4", "2021T1", "2021T1"]
    assert set(out["IPCF"]) == {"1500,50"}                  # decimal unificado
    assert out["isco08_2d"].dropna().tolist() == ["24", "24"]
    assert out["PP09A_ESP"].dropna().tolist() == ["A&ntilde;elo", "A&ntilde;elo"]
    assert (tmp_path / "eph_isco08_cobertura.csv").exists()


def test_carpeta_vacia(tmp_path, monkeypatch):
    (tmp_path / "microdatos").mkdir()
    monkeypatch.chdir(tmp_path)
    assert main(["microdatos"]) == 1
    assert not (tmp_path / "eph_isco08.csv").exists()
