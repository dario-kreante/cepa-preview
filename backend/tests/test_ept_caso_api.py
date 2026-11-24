import pytest


def _payload(ingreso_id, **over):
    base = {
        "ingreso_id": ingreso_id,
        "mes": "2026-06",
        "fecha_ingreso_ept": "2026-01-10",
        "nombre_trabajador": "Pedro Soto",
        "rut_trabajador": "12.345.678-5",
        "region_trabajador": "Maule",
        "eista": "Ana González",
        "factor_riesgo": "sobrecarga",
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

def _segundo_ingreso(db_session, ingreso_fixture, folio="F-2026-TEST-2"):
    import datetime

    from app.models.ingreso import Ingreso

    otro = Ingreso(
        paciente_id=ingreso_fixture.paciente_id,
        folio=folio,
        folio_manual=True,
        fecha_ingreso=datetime.date(2026, 5, 1),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        estado="activo",
    )
    db_session.add(otro)
    db_session.flush()
    return otro


def test_listar_casos_ept_por_paciente(as_admin, db_session, ingreso_fixture):
    """QA-009: una EPT por folio; el listado trae folio, fecha del ingreso y plazos."""
    otro = _segundo_ingreso(db_session, ingreso_fixture)
    viejo = as_admin.post(
        "/api/v1/casos-ept", json=_payload(ingreso_fixture.id, fecha_ingreso_ept="2026-01-10")
    ).json()
    nuevo = as_admin.post(
        "/api/v1/casos-ept", json=_payload(otro.id, fecha_ingreso_ept="2026-05-01")
    ).json()
    as_admin.post(f"/api/v1/casos-ept/{viejo['id']}/plazos", json={"caso_ept_id": viejo["id"]})
    r = as_admin.get("/api/v1/casos-ept", params={"paciente_id": ingreso_fixture.paciente_id})
    assert r.status_code == 200, r.text
    filas = r.json()
    assert [c["id"] for c in filas] == [nuevo["id"], viejo["id"]]
    assert filas[0]["folio"] == "F-2026-TEST-2"
    assert filas[0]["fecha_ingreso"] == "2026-05-01"
    assert filas[0]["plazo_informe_ept"] is None
    assert filas[1]["folio"] == "F-2026-TEST"
    assert filas[1]["plazo_informe_ept"] == "2026-01-23"
    assert filas[1]["plazo_portal_isl"] == "2026-01-29"
    assert filas[1]["fecha_envio"] is None


# ── QA-009: una EPT por folio y precarga desde el paciente y su ingreso ──


def test_segunda_ept_del_mismo_ingreso_da_409(as_admin, ingreso_fixture):
    primero = as_admin.post("/api/v1/casos-ept", json=_payload(ingreso_fixture.id))
    assert primero.status_code == 201
    r = as_admin.post("/api/v1/casos-ept", json=_payload(ingreso_fixture.id))
    assert r.status_code == 409, r.text
    detalle = r.json()["detail"]
    assert "F-2026-TEST" in detalle
    assert f"caso N° {primero.json()['id']}" in detalle


def test_crear_ept_en_ingreso_inexistente_da_404(as_admin):
    r = as_admin.post("/api/v1/casos-ept", json=_payload(999999))
    assert r.status_code == 404


def test_crear_caso_sin_datos_del_trabajador_los_toma_del_paciente_e_ingreso(
    as_admin, ingreso_fixture
):
    r = as_admin.post(
        "/api/v1/casos-ept",
        json={
            "ingreso_id": ingreso_fixture.id,
            "eista": "Ana González",
            "factor_riesgo": "sobrecarga",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["nombre_trabajador"] == "Pedro Soto"
    assert body["rut_trabajador"] == "123456785"
    assert body["region_trabajador"] == "Maule"
    assert body["fecha_ingreso_ept"] == "2026-01-10"  # fecha del ingreso
    assert body["mes"] == "Enero 2026"


def test_crear_caso_sin_region_y_paciente_sin_region_da_422(
    as_admin, db_session, ingreso_fixture
):
    ingreso_fixture.paciente.region = None
    db_session.flush()
    r = as_admin.post(
        "/api/v1/casos-ept",
        json={"ingreso_id": ingreso_fixture.id, "eista": "A", "factor_riesgo": "sobrecarga"},
    )
    assert r.status_code == 422, r.text
    assert "región" in r.json()["detail"]


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


# ── QA UTalca 22-10 QA-003: factores de riesgo del área EPT ──

def _caso_legado(db_session, ingreso_fixture, factor="carga"):
    """Inserta un caso con un factor de riesgo legado, como los que ya existen en dev/QA."""
    import datetime

    from app.models.ept import CasoEpt

    caso = CasoEpt(
        ingreso_id=ingreso_fixture.id,
        mes="2026-06",
        fecha_ingreso_ept=datetime.date(2026, 1, 10),
        nombre_trabajador="Pedro Soto",
        rut_trabajador="123456785",
        region_trabajador="Maule",
        eista="Ana González",
        factor_riesgo=factor,
        corresponde_ept=True,
        estado="abierto",
    )
    db_session.add(caso)
    db_session.commit()
    return caso.id


def test_crear_caso_con_cada_factor_nuevo(as_admin, ingreso_fixture):
    from app.domain.enums_ept import FactorRiesgo

    for factor in FactorRiesgo:
        r = as_admin.post(
            "/api/v1/casos-ept", json=_payload(ingreso_fixture.id, factor_riesgo=factor.value)
        )
        assert r.status_code == 201, (factor, r.text)
        assert r.json()["factor_riesgo"] == factor.value
        # QA-009: un folio admite una sola EPT; se borra para probar el siguiente factor.
        assert as_admin.delete(f"/api/v1/casos-ept/{r.json()['id']}").status_code == 204


def test_crear_caso_con_factor_legado_rechazado(as_admin, ingreso_fixture):
    r = as_admin.post(
        "/api/v1/casos-ept", json=_payload(ingreso_fixture.id, factor_riesgo="carga")
    )
    assert r.status_code == 422


def test_caso_legado_se_lee_y_lista(as_admin, db_session, ingreso_fixture):
    from app.domain.enums_ept import FactorRiesgoLegado

    ids = [
        _caso_legado(db_session, ingreso_fixture, factor=f.value) for f in FactorRiesgoLegado
    ]
    for caso_id, factor in zip(ids, FactorRiesgoLegado):
        r = as_admin.get(f"/api/v1/casos-ept/{caso_id}")
        assert r.status_code == 200, r.text
        assert r.json()["factor_riesgo"] == factor.value

    r = as_admin.get("/api/v1/casos-ept", params={"paciente_id": ingreso_fixture.paciente_id})
    assert r.status_code == 200, r.text
    assert sorted(c["id"] for c in r.json()) == sorted(ids)


def test_editar_caso_legado_con_factor_nuevo(as_admin, db_session, ingreso_fixture):
    caso_id = _caso_legado(db_session, ingreso_fixture)
    r = as_admin.patch(f"/api/v1/casos-ept/{caso_id}", json={"factor_riesgo": "hostilidad_pares"})
    assert r.status_code == 200, r.text
    assert r.json()["factor_riesgo"] == "hostilidad_pares"


def test_editar_caso_legado_sin_tocar_factor(as_admin, db_session, ingreso_fixture):
    caso_id = _caso_legado(db_session, ingreso_fixture)
    r = as_admin.patch(f"/api/v1/casos-ept/{caso_id}", json={"eista": "Otra EISTA"})
    assert r.status_code == 200, r.text
    assert r.json()["factor_riesgo"] == "carga"


def test_editar_caso_a_factor_legado_rechazado(as_admin, ingreso_fixture):
    caso_id = as_admin.post("/api/v1/casos-ept", json=_payload(ingreso_fixture.id)).json()["id"]
    r = as_admin.patch(f"/api/v1/casos-ept/{caso_id}", json={"factor_riesgo": "otro"})
    assert r.status_code == 422


# Reunión 29-10 (D11): hasta 3 factores de riesgo (principal + 2 adicionales).
def test_caso_con_factores_adicionales(as_admin, ingreso_fixture):
    r = as_admin.post(
        "/api/v1/casos-ept",
        json=_payload(ingreso_fixture.id, factores_adicionales=["subcarga", "hostilidad_jefatura"]),
    )
    assert r.status_code == 201, r.text
    caso = r.json()
    assert caso["factor_riesgo"] == "sobrecarga"
    assert caso["factores_adicionales"] == ["subcarga", "hostilidad_jefatura"]

    r = as_admin.patch(f"/api/v1/casos-ept/{caso['id']}", json={"factores_adicionales": []})
    assert r.status_code == 200, r.text
    assert r.json()["factores_adicionales"] == []


@pytest.mark.parametrize(
    "adicionales",
    [
        ["subcarga", "hostilidad_jefatura", "asedio_sexual"],  # 4 en total
        ["subcarga", "subcarga"],  # repetido
        ["sobrecarga"],  # repite el principal
    ],
)
def test_factores_adicionales_invalidos(as_admin, ingreso_fixture, adicionales):
    r = as_admin.post(
        "/api/v1/casos-ept",
        json=_payload(ingreso_fixture.id, factores_adicionales=adicionales),
    )
    assert r.status_code == 422


def test_cambiar_el_principal_a_uno_adicional_lo_saca_de_los_adicionales(as_admin, ingreso_fixture):
    caso = as_admin.post(
        "/api/v1/casos-ept",
        json=_payload(ingreso_fixture.id, factores_adicionales=["subcarga"]),
    ).json()
    r = as_admin.patch(f"/api/v1/casos-ept/{caso['id']}", json={"factor_riesgo": "subcarga"})
    assert r.status_code == 200, r.text
    assert (r.json()["factor_riesgo"], r.json()["factores_adicionales"]) == ("subcarga", [])
