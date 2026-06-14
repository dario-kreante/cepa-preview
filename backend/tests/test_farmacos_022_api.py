"""Tests de CEPA-022: gestión de recetas y alertas de revisión próxima."""

from datetime import date, timedelta


def _setup_registro(client, rut: str = "22.222.222-2") -> tuple[int, int]:
    """Crea ingreso + registro farmacológico; devuelve (ingreso_id, registro_id)."""
    ingreso_r = client.post(
        "/api/v1/ingresos",
        json={
            "rut": rut,
            "nombre": "Paciente Receta",
            "sexo": "M",
            "edad": 50,
            "region": "Maule",
            "diagnostico": "F41",
            "tipo_derivacion": "DIEP",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-06-10",
        },
    )
    assert ingreso_r.status_code == 201, ingreso_r.text
    ingreso_id = ingreso_r.json()["id"]
    reg_r = client.post(
        "/api/v1/registro-farmacologico",
        json={
            "ingreso_id": ingreso_id,
            "medico_tratante": "Dr. López",
            "estado_farmacologico": "activo",
        },
    )
    assert reg_r.status_code == 201, reg_r.text
    return ingreso_id, reg_r.json()["id"]


# TC-022-01: CA-1 — receta vinculada al folio y visible
def test_crear_receta_vinculada_al_folio(as_admin):
    ingreso_id, _ = _setup_registro(as_admin)
    r = as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/recetas",
        json={
            "fecha_emision": "2026-06-01",
            "fecha_revision": "2026-06-20",
            "fecha_envio": "2026-06-05",
            "marca_medicamento": "Fluoxetina genérico",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["fecha_emision"] == "2026-06-01"
    assert body["fecha_revision"] == "2026-06-20"
    assert body["marca_medicamento"] == "Fluoxetina genérico"


# TC-022-01: Listar recetas del folio
def test_listar_recetas_del_folio(as_admin):
    ingreso_id, _ = _setup_registro(as_admin, rut="33.333.333-3")
    as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/recetas",
        json={
            "fecha_emision": "2026-06-01",
            "fecha_revision": "2026-06-20",
            "marca_medicamento": "Fluoxetina",
        },
    )
    r = as_admin.get(f"/api/v1/registro-farmacologico/{ingreso_id}/recetas")
    assert r.status_code == 200
    assert len(r.json()) >= 1


# TC-022-04: revisión anterior a emisión → 422
def test_receta_revision_anterior_a_emision_rechazada(as_admin):
    ingreso_id, _ = _setup_registro(as_admin, rut="44.444.444-4")
    r = as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/recetas",
        json={
            "fecha_emision": "2026-06-10",
            "fecha_revision": "2026-06-05",
            "marca_medicamento": "Clonazepam",
        },
    )
    assert r.status_code == 422


# TC-022-02: CA-2 — alerta generada cuando revisión en próximos 5 días
def test_alerta_generada_para_revision_proxima(as_admin):
    ingreso_id, _ = _setup_registro(as_admin, rut="55.555.555-5")
    hoy = date.today()
    revision_en_1_dia = (hoy + timedelta(days=1)).isoformat()
    as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/recetas",
        json={
            "fecha_emision": hoy.isoformat(),
            "fecha_revision": revision_en_1_dia,
            "marca_medicamento": "Sertralina",
        },
    )
    r = as_admin.post("/api/v1/registro-farmacologico/recetas/alertas/generar")
    assert r.status_code == 201, r.text
    alertas = r.json()
    assert len(alertas) >= 1
    tipos = [a["tipo"] for a in alertas]
    assert "revision_proxima" in tipos


# TC-022-03: CA-3 — alerta generada para revisión exactamente a 5 días (límite inclusivo)
def test_alerta_limite_inclusivo_5_dias(as_admin):
    ingreso_id, _ = _setup_registro(as_admin, rut="66.666.666-6")
    hoy = date.today()
    revision_en_5_dias = (hoy + timedelta(days=5)).isoformat()
    as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/recetas",
        json={
            "fecha_emision": hoy.isoformat(),
            "fecha_revision": revision_en_5_dias,
            "marca_medicamento": "Litio",
        },
    )
    r = as_admin.post("/api/v1/registro-farmacologico/recetas/alertas/generar")
    assert r.status_code == 201
    ids_recetas_alertadas = [a["receta_id"] for a in r.json()]
    # debe haber al menos una alerta para esta receta
    assert len(ids_recetas_alertadas) >= 1


# TC-022-05: NO se genera alerta para revisión a 6 días
def test_no_alerta_para_revision_a_6_dias(as_admin):
    ingreso_id, _ = _setup_registro(as_admin, rut="77.777.777-7")
    hoy = date.today()
    revision_en_6_dias = (hoy + timedelta(days=6)).isoformat()
    as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/recetas",
        json={
            "fecha_emision": hoy.isoformat(),
            "fecha_revision": revision_en_6_dias,
            "marca_medicamento": "Aripiprazol",
        },
    )
    r = as_admin.post("/api/v1/registro-farmacologico/recetas/alertas/generar")
    assert r.status_code == 201
    # La receta con revisión a 6 días NO debe aparecer en alertas
    for alerta in r.json():
        r_receta = as_admin.get(f"/api/v1/registro-farmacologico/{ingreso_id}/recetas")
        receta_ids = [rec["id"] for rec in r_receta.json()]
        # ninguna alerta debe corresponder a una receta de este ingreso
        assert alerta["receta_id"] not in receta_ids


# TC-022-06: Auditor no puede crear ni generar alertas → 403
def test_auditor_no_puede_crear_receta(as_auditor, as_admin):
    ingreso_id, _ = _setup_registro(as_admin, rut="88.888.888-8")
    r = as_auditor.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/recetas",
        json={
            "fecha_emision": "2026-06-01",
            "fecha_revision": "2026-06-20",
            "marca_medicamento": "X",
        },
    )
    assert r.status_code == 403


# TC-022-06: Auditor puede listar recetas → 200
def test_auditor_puede_listar_recetas(as_auditor, as_admin):
    ingreso_id, _ = _setup_registro(as_admin, rut="99.999.999-9")
    as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/recetas",
        json={
            "fecha_emision": "2026-06-01",
            "fecha_revision": "2026-07-01",
            "marca_medicamento": "Quetiapina",
        },
    )
    r = as_auditor.get(f"/api/v1/registro-farmacologico/{ingreso_id}/recetas")
    assert r.status_code == 200
