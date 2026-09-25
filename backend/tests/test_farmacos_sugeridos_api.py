"""Fármacos sugeridos desde las recetas de SALUTEM, para revisión humana.

GET /api/v1/registro-farmacologico/{ingreso_id}/sugeridos lee las fichas de SALUTEM
del ingreso, estructura cada medicamento recetado y dice si ya está en el esquema
o si su receta ya se registró. No escribe nada.
"""

import pytest


@pytest.fixture
def ingreso(as_admin) -> dict:
    r = as_admin.post(
        "/api/v1/ingresos",
        json={
            "rut": "7.876.543-7",
            "nombre": "Paciente Fármacos",
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
    return r.json()


def _ficha(cliente, folio, cita_id, cita_fecha, receta, *, tipo="Receta Medicamentos", origen="SALUTEM"):
    r = cliente.post(
        "/api/v1/fichas-clinicas",
        json={
            "folio": folio,
            "origen": origen,
            "contenido": {
                "citaId": cita_id,
                "citaFecha": cita_fecha,
                "especialidadNombre": "Médico/a",
                "profesionalNombre": "DR. JORGE SOTOMAYOR",
                "indicaciones": [{"tipo": tipo, "nombre": "Receta", "registro": receta}],
            },
        },
    )
    assert r.status_code == 201, r.text


def _url(ingreso):
    return f"/api/v1/registro-farmacologico/{ingreso['id']}/sugeridos"


def test_estructura_cada_medicamento_de_la_receta(as_admin, ingreso):
    _ficha(as_admin, ingreso["folio"], 1, "2024-04-05", "Clotiazepam 5 mg SOS\r\n\r\nSertralina 100 mg 1 al día")

    r = as_admin.get(_url(ingreso))

    assert r.status_code == 200, r.text
    por_med = {s["medicamento"]: s for s in r.json()}
    assert set(por_med) == {"Clotiazepam", "Sertralina"}
    s = por_med["Sertralina"]
    assert (s["dosis"], s["frecuencia"], s["cita_fecha"]) == ("100 mg", "c/24h", "2024-04-05")
    assert s["profesional"] == "DR. JORGE SOTOMAYOR"
    assert (s["en_esquema"], s["receta_registrada"]) == (False, False)
    assert por_med["Clotiazepam"]["frecuencia"] == "otro"
    assert por_med["Clotiazepam"]["avisos"]


def test_el_mismo_medicamento_en_varios_controles_se_sugiere_una_vez_con_el_mas_reciente(as_admin, ingreso):
    _ficha(as_admin, ingreso["folio"], 1, "2024-04-05", "Sertralina 100 mg 1 al día")
    _ficha(as_admin, ingreso["folio"], 2, "2024-08-29", "Sertralina 100 mg 1 comp cada 24 horas")

    [s] = as_admin.get(_url(ingreso)).json()

    assert s["cita_fecha"] == "2024-08-29"


def test_ignora_indicaciones_que_no_son_recetas_y_fichas_que_no_son_de_salutem(as_admin, ingreso):
    _ficha(as_admin, ingreso["folio"], 1, "2024-04-05", "Sertralina 100 mg 1 al día", tipo="Indicación")
    _ficha(as_admin, ingreso["folio"], 2, "2024-04-05", "Sertralina 100 mg 1 al día", origen="IMED")
    _ficha(as_admin, ingreso["folio"], 3, "2024-04-05", "fsdfsdff")

    assert as_admin.get(_url(ingreso)).json() == []


def test_marca_lo_que_ya_esta_en_el_esquema_y_la_receta_registrada(as_admin, ingreso):
    _ficha(as_admin, ingreso["folio"], 1, "2024-04-05", "Sertralina 100 mg 1 al día")
    ingreso_id = ingreso["id"]
    as_admin.post(
        "/api/v1/registro-farmacologico",
        json={"ingreso_id": ingreso_id, "medico_tratante": "Dr. Sotomayor", "estado_farmacologico": "activo"},
    ).raise_for_status()
    as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/esquema",
        json={"medicamento": "sertralina", "dosis": "100 mg", "frecuencia": "c/24h"},
    ).raise_for_status()
    as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/recetas",
        json={"fecha_emision": "2024-04-05", "fecha_revision": "2024-05-05", "marca_medicamento": "Sertralina 100 mg"},
    ).raise_for_status()

    [s] = as_admin.get(_url(ingreso)).json()

    assert (s["en_esquema"], s["receta_registrada"]) == (True, True)


def test_ingreso_inexistente_responde_404(as_admin):
    assert as_admin.get("/api/v1/registro-farmacologico/999999/sugeridos").status_code == 404


def test_el_auditor_puede_leer_las_sugerencias(as_auditor):
    r = as_auditor.get("/api/v1/registro-farmacologico/999999/sugeridos")
    assert r.status_code == 404  # llega al endpoint (no 403)
