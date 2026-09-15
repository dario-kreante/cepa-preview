"""Licencias sugeridas desde las atenciones de SALUTEM, para revisión humana.

GET /api/v1/fichas-clinicas/{folio}/licencias-sugeridas lee las fichas de
SALUTEM ya importadas, extrae las licencias de sus indicaciones y las devuelve
como sugerencias. No escribe nada: el administrativo revisa cada una y la
registra con el alta de licencia de siempre.
"""

import pytest

EXTENSION_TIPO_6 = (
    "<span>Extiendo licencia médica&nbsp;<b>tipo 6 total&nbsp;</b>desde\r\nel&nbsp;"
    "<b>09/05/2024&nbsp;</b>por&nbsp;<b>21 días</b>, dado por moderado grado de\r\n"
    "discapacidad o interferencia con&nbsp;sus actividades cotidianas.</span>"
)


@pytest.fixture
def folio(as_admin) -> str:
    r = as_admin.post(
        "/api/v1/ingresos",
        json={
            "rut": "7.876.543-7",
            "nombre": "Paciente Sugerencias",
            "sexo": "F",
            "edad": 40,
            "region": "Maule",
            "diagnostico": "Trastorno adaptativo",
            "tipo_derivacion": "DIEP",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2024-03-01",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["folio"]


def _ficha(cliente, folio: str, cita_fecha: str, *registros, origen: str = "SALUTEM") -> None:
    r = cliente.post(
        "/api/v1/fichas-clinicas",
        json={
            "folio": folio,
            "origen": origen,
            "contenido": {
                "citaId": 1000 + len(registros),
                "citaFecha": cita_fecha,
                "especialidadNombre": "Medicina del trabajo",
                "indicaciones": [
                    {"tipo": 1, "nombre": "Indicaciones", "registro": reg} for reg in registros
                ],
            },
        },
    )
    assert r.status_code == 201, r.text


def _ingreso_id(cliente, folio: str) -> int:
    ingresos = cliente.get("/api/v1/ingresos").json()
    return next(i["id"] for i in ingresos if i["folio"] == folio)


def test_sugiere_la_licencia_escrita_en_la_indicacion(as_admin, folio):
    _ficha(as_admin, folio, "2024-05-06", EXTENSION_TIPO_6)

    r = as_admin.get(f"/api/v1/fichas-clinicas/{folio}/licencias-sugeridas")

    assert r.status_code == 200, r.text
    sugerencias = r.json()
    assert len(sugerencias) == 1
    s = sugerencias[0]
    assert s["cita_fecha"] == "2024-05-06"
    assert s["tipo_lm"] == "6"
    assert s["tipo_reposo"] == "total"
    assert s["origen"] == "sistema"
    assert s["fecha_inicio"] == "2024-05-09"
    assert s["fecha_termino"] == "2024-05-29"
    assert s["termino_calculado"] is True
    assert s["cantidad_dias"] == 21
    assert s["avisos"] == []
    assert s["ya_registrada"] is False
    assert "Extiendo licencia médica" in s["texto"]


def test_ignora_altas_farmacos_y_fichas_que_no_son_de_salutem(as_admin, folio):
    _ficha(
        as_admin,
        folio,
        "2024-06-12",
        "<p><b>Alta laboral Total:</b> reincorporación a partir del <b>14/06/2024.</b></p>",
        "Sertralina 50 mg: 1 comprimido cada mañana por 30 días",
        "<p>Paciente se encuentra sin licencia medica</p>",
    )
    _ficha(as_admin, folio, "2024-05-06", EXTENSION_TIPO_6, origen="SAM")

    r = as_admin.get(f"/api/v1/fichas-clinicas/{folio}/licencias-sugeridas")

    assert r.status_code == 200, r.text
    assert r.json() == []


def test_la_misma_licencia_mencionada_dos_veces_se_sugiere_una_vez(as_admin, folio):
    _ficha(
        as_admin,
        folio,
        "2024-04-05",
        "Control médico previo a vencimiento de licencia extrasistema (17/04/2024)",
        "Paciente se encuentra con licencia médica extrasistema hasta el 17/04/24",
    )

    sugerencias = as_admin.get(f"/api/v1/fichas-clinicas/{folio}/licencias-sugeridas").json()

    assert len(sugerencias) == 1
    assert sugerencias[0]["origen"] == "extra_sistema"
    assert sugerencias[0]["fecha_termino"] == "2024-04-17"


def test_marca_la_sugerencia_si_la_licencia_ya_esta_registrada(as_admin, folio):
    _ficha(as_admin, folio, "2024-05-06", EXTENSION_TIPO_6)
    registrada = as_admin.post(
        "/api/v1/licencias",
        json={
            "ingreso_id": _ingreso_id(as_admin, folio),
            "tipo_lm": "6",
            "tipo_reposo": "total",
            "fecha_inicio": "2024-05-09",
            "fecha_termino": "2024-05-29",
            "fecha_emision": "2024-05-06",
            "inicio_reposo": "2024-05-09",
            "fin_reposo": "2024-05-29",
            "cantidad_dias": 21,
            "diagnostico": "Trastorno adaptativo",
        },
    )
    assert registrada.status_code == 201, registrada.text

    sugerencias = as_admin.get(f"/api/v1/fichas-clinicas/{folio}/licencias-sugeridas").json()

    assert len(sugerencias) == 1
    assert sugerencias[0]["ya_registrada"] is True


def test_tipo_fuera_del_catalogo_no_se_sugiere_y_avisa(as_admin, folio):
    _ficha(
        as_admin,
        folio,
        "2024-05-06",
        "Extiendo licencia médica tipo 3 total desde el 09/05/2024 por 10 días",
    )

    s = as_admin.get(f"/api/v1/fichas-clinicas/{folio}/licencias-sugeridas").json()[0]

    assert s["tipo_lm"] is None
    assert any("catálogo" in a for a in s["avisos"])


def test_auditor_puede_ver_las_sugerencias(as_admin, as_auditor, folio):
    _ficha(as_admin, folio, "2024-05-06", EXTENSION_TIPO_6)

    r = as_auditor.get(f"/api/v1/fichas-clinicas/{folio}/licencias-sugeridas")

    assert r.status_code == 200
    assert len(r.json()) == 1


def test_folio_inexistente_da_404(as_admin):
    r = as_admin.get("/api/v1/fichas-clinicas/F-NO-EXISTE/licencias-sugeridas")
    assert r.status_code == 404
