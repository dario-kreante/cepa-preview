"""Programa del ingreso (Programa Regular / Ley Karin / PIPT): alta, edición y lectura.

Los reportes filtran por `Ingreso.programa`; el formulario debe poder guardarlo.
Un valor antiguo fuera de la lista se conserva tal cual (no se rechaza ni se pierde).
"""


def _payload(**over):
    base = {
        "rut": "12.345.678-5",
        "nombre": "Juan Pérez",
        "sexo": "M",
        "edad": 40,
        "region": "Maule",
        "diagnostico": "Trastorno adaptativo",
        "tipo_derivacion": "DIAT",
        "tipo_ingreso": "convenio",
        "modelo_tratamiento": "ambulatorio",
        "fecha_ingreso": "2026-06-10",
    }
    base.update(over)
    return base


def test_crear_ingreso_guarda_programa_y_lo_devuelve(as_admin):
    r = as_admin.post("/api/v1/ingresos", json=_payload(programa="Ley Karin"))
    assert r.status_code == 201, r.text
    assert r.json()["programa"] == "Ley Karin"

    releido = as_admin.get(f"/api/v1/ingresos/{r.json()['id']}")
    assert releido.status_code == 200, releido.text
    assert releido.json()["programa"] == "Ley Karin"


def test_crear_ingreso_sin_programa_queda_vacio(as_admin):
    r = as_admin.post("/api/v1/ingresos", json=_payload())
    assert r.status_code == 201, r.text
    assert r.json()["programa"] is None


def test_crear_ingreso_con_programa_en_blanco_queda_vacio(as_admin):
    r = as_admin.post("/api/v1/ingresos", json=_payload(programa="   "))
    assert r.status_code == 201, r.text
    assert r.json()["programa"] is None


def _crear(cliente, **over) -> dict:
    r = cliente.post("/api/v1/ingresos", json=_payload(**over))
    assert r.status_code == 201, r.text
    return r.json()


def test_editar_ingreso_cambia_programa(as_admin):
    ingreso = _crear(as_admin)

    r = as_admin.put(f"/api/v1/ingresos/{ingreso['id']}", json={"programa": "PIPT"})
    assert r.status_code == 200, r.text
    assert r.json()["programa"] == "PIPT"


def test_editar_ingreso_a_sin_programa_guarda_vacio(as_admin):
    ingreso = _crear(as_admin, programa="Programa Regular")

    r = as_admin.put(f"/api/v1/ingresos/{ingreso['id']}", json={"programa": None})
    assert r.status_code == 200, r.text
    assert r.json()["programa"] is None


def test_editar_ingreso_sin_enviar_programa_no_lo_toca(as_admin):
    ingreso = _crear(as_admin, programa="Ley Karin")

    r = as_admin.put(f"/api/v1/ingresos/{ingreso['id']}", json={"diagnostico": "Otro"})
    assert r.status_code == 200, r.text
    assert r.json()["programa"] == "Ley Karin"


def test_editar_ingreso_conserva_programa_antiguo_fuera_de_la_lista(as_admin):
    """Un programa antiguo (p. ej. 'DIEP') no se rechaza al editar la ficha."""
    ingreso = _crear(as_admin, programa="DIEP")

    r = as_admin.put(
        f"/api/v1/ingresos/{ingreso['id']}",
        json={"programa": "DIEP", "diagnostico": "Trastorno de ansiedad"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["programa"] == "DIEP"
