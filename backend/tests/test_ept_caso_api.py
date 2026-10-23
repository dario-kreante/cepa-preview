def _payload(ingreso_id, **over):
    base = {
        "ingreso_id": ingreso_id,
        "mes": "2026-06",
        "fecha_ingreso_ept": "2026-01-10",
        "nombre_trabajador": "Pedro Soto",
        "rut_trabajador": "12.345.678-5",
        "region_trabajador": "Maule",
        "eista": "Ana González",
        "factor_riesgo": "carga",
        "corresponde_ept": True,
        "razon_social": "Empresa XY SA",
        "unidad_cargo_horario": "Bodega / Bodeguero / turno mañana",
    }
    base.update(over)
    return base


# TC-030-01: creación completa — caso creado, auditoría registrada
def test_crear_caso_ept_completo(as_admin, db_session, ingreso_fixture):
    r = as_admin.post("/api/v1/casos-ept", json=_payload(ingreso_fixture.id))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["id"] >= 1
    assert body["estado"] == "abierto"
    assert body["corresponde_ept"] is True
    assert body["rut_trabajador"] == "123456785"  # normalizado

    # visible al leer por id
    r2 = as_admin.get(f"/api/v1/casos-ept/{body['id']}")
    assert r2.status_code == 200
    assert r2.json()["id"] == body["id"]


# TC-030-02: RUT con DV inválido rechazado con 422
def test_rut_invalido_retorna_422(as_admin, ingreso_fixture):
    r = as_admin.post(
        "/api/v1/casos-ept",
        json=_payload(ingreso_fixture.id, rut_trabajador="12.345.678-0"),
    )
    assert r.status_code == 422
    assert "rut" in r.text.lower()


# TC-030-03: tercer contacto rechazado
def test_tercer_contacto_rechazado(as_admin, db_session, ingreso_fixture):
    r = as_admin.post("/api/v1/casos-ept", json=_payload(ingreso_fixture.id))
    caso_id = r.json()["id"]
    as_admin.post(f"/api/v1/casos-ept/{caso_id}/contactos", json={"correo": "a@b.cl"})
    as_admin.post(f"/api/v1/casos-ept/{caso_id}/contactos", json={"correo": "c@d.cl"})
    r3 = as_admin.post(f"/api/v1/casos-ept/{caso_id}/contactos", json={"correo": "e@f.cl"})
    assert r3.status_code == 400
    assert "máximo" in r3.text.lower() or "max" in r3.text.lower()


# TC-030-04: corresponde_ept=False — caso creado con estado no_corresponde
def test_corresponde_ept_false(as_admin, ingreso_fixture):
    r = as_admin.post(
        "/api/v1/casos-ept",
        json=_payload(ingreso_fixture.id, corresponde_ept=False),
    )
    assert r.status_code == 201
    assert r.json()["estado"] == "no_corresponde"
    assert r.json()["corresponde_ept"] is False


# TC-030-05: Auditor no puede crear (solo lectura) → 403
def test_auditor_no_puede_crear(as_auditor, ingreso_fixture):
    r = as_auditor.post("/api/v1/casos-ept", json=_payload(ingreso_fixture.id))
    assert r.status_code == 403


# TC-030-06: campo factor_riesgo vacío / inválido → 422
def test_factor_riesgo_invalido_rechazado(as_admin, ingreso_fixture):
    r = as_admin.post(
        "/api/v1/casos-ept",
        json=_payload(ingreso_fixture.id, factor_riesgo="invalido_xyz"),
    )
    assert r.status_code == 422


# CA-5: Auditor y Coordinacion pueden leer en solo lectura
def test_auditor_puede_leer(as_admin, as_auditor, ingreso_fixture):
    caso_id = as_admin.post(
        "/api/v1/casos-ept", json=_payload(ingreso_fixture.id)
    ).json()["id"]
    r = as_auditor.get(f"/api/v1/casos-ept/{caso_id}")
    assert r.status_code == 200
    assert r.json()["id"] == caso_id


def test_coordinacion_puede_leer(as_admin, as_coordinacion, ingreso_fixture):
    caso_id = as_admin.post(
        "/api/v1/casos-ept", json=_payload(ingreso_fixture.id)
    ).json()["id"]
    r = as_coordinacion.get(f"/api/v1/casos-ept/{caso_id}")
    assert r.status_code == 200


# ── QA Pilar 22-10 QA-003: listar EPT del paciente y borrar las creadas por error ──

def test_listar_casos_ept_por_paciente(as_admin, ingreso_fixture):
    viejo = as_admin.post(
        "/api/v1/casos-ept", json=_payload(ingreso_fixture.id, fecha_ingreso_ept="2026-01-10")
    ).json()
    nuevo = as_admin.post(
        "/api/v1/casos-ept", json=_payload(ingreso_fixture.id, fecha_ingreso_ept="2026-05-01")
    ).json()
    r = as_admin.get("/api/v1/casos-ept", params={"paciente_id": ingreso_fixture.paciente_id})
    assert r.status_code == 200, r.text
    assert [c["id"] for c in r.json()] == [nuevo["id"], viejo["id"]]


def test_listar_casos_ept_paciente_sin_casos(as_auditor, ingreso_fixture):
    r = as_auditor.get("/api/v1/casos-ept", params={"paciente_id": ingreso_fixture.paciente_id})
    assert r.status_code == 200
    assert r.json() == []


def test_eliminar_caso_ept_borra_dependientes_y_resuelve_alertas(
    as_admin, db_session, ingreso_fixture
):
    from datetime import datetime, timezone

    from sqlalchemy import select

    from app.models.alertas import AlertaNotif
    from app.models.audit_log import AuditLog
    from app.models.ept import ContactoEpt, PlazoEpt

    caso_id = as_admin.post("/api/v1/casos-ept", json=_payload(ingreso_fixture.id)).json()["id"]
    as_admin.post(f"/api/v1/casos-ept/{caso_id}/contactos", json={"correo": "a@b.cl"})
    plazo = as_admin.post(
        f"/api/v1/casos-ept/{caso_id}/plazos",
        json={"caso_ept_id": caso_id, "plazo_informe_ept": "2026-12-31"},
    ).json()
    alerta = AlertaNotif(
        tipo="plazo_ept",
        estado="pendiente",
        caso_id=plazo["id"],
        caso_tipo="ept",
        plazo_objetivo=datetime(2026, 12, 31, tzinfo=timezone.utc),
        ventana_dias=5,
    )
    db_session.add(alerta)
    db_session.commit()

    r = as_admin.delete(f"/api/v1/casos-ept/{caso_id}")
    assert r.status_code == 204, r.text
    assert as_admin.get(f"/api/v1/casos-ept/{caso_id}").status_code == 404
    assert db_session.scalars(select(ContactoEpt).where(ContactoEpt.caso_ept_id == caso_id)).all() == []
    assert db_session.scalars(select(PlazoEpt).where(PlazoEpt.caso_ept_id == caso_id)).all() == []
    db_session.refresh(alerta)
    assert alerta.estado == "resuelta"
    traza = db_session.scalars(
        select(AuditLog).where(AuditLog.entity == "caso_ept", AuditLog.action == "DELETE")
    ).one()
    assert traza.entity_id == str(caso_id)


def test_auditor_no_puede_eliminar_caso_ept(as_admin, as_auditor, ingreso_fixture):
    caso_id = as_admin.post("/api/v1/casos-ept", json=_payload(ingreso_fixture.id)).json()["id"]
    assert as_auditor.delete(f"/api/v1/casos-ept/{caso_id}").status_code == 403


def test_eliminar_caso_ept_inexistente_404(as_admin):
    assert as_admin.delete("/api/v1/casos-ept/999999").status_code == 404
