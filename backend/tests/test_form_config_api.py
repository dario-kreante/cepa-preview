"""Tests de integración para el editor de formularios dinámicos (CEPA-110 / CEPA-111)."""

from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog


def _campos_sistema():
    """Payload mínimo con los 7 campos obligatorios bien parametrizados."""
    return [
        {"field_key": "sexo",       "label": "Sexo",                 "field_type": "select",  "required": True,  "system_locked": True,  "domain_values": ["F","M","otro"],                                      "display_order": 1},
        {"field_key": "edad",       "label": "Edad",                 "field_type": "number",  "required": True,  "system_locked": True,  "domain_values": None,                                                  "display_order": 2},
        {"field_key": "diagnostico","label": "Diagnóstico",          "field_type": "text",    "required": True,  "system_locked": True,  "domain_values": None,                                                  "display_order": 3},
        {"field_key": "modelo_trat","label": "Modelo de tratamiento","field_type": "text",    "required": True,  "system_locked": True,  "domain_values": None,                                                  "display_order": 4},
        {"field_key": "tipo_alta",  "label": "Tipo de alta",         "field_type": "select",  "required": True,  "system_locked": True,  "domain_values": ["terapeutica","medica","psicologica","abandono","derivacion"], "display_order": 5},
        {"field_key": "tipo_ingreso","label": "Tipo de ingreso",     "field_type": "select",  "required": True,  "system_locked": True,  "domain_values": ["consulta_espontanea","convenio","proyecto","particular"], "display_order": 6},
        {"field_key": "tipo_convenio","label": "Tipo de convenio",   "field_type": "select",  "required": True,  "system_locked": True,  "domain_values": ["ISL","SUSESO","particular","otro"],                   "display_order": 7},
    ]


# CA-4: usuario sin perfil Coordinacion no puede acceder al editor → 403
def test_admin_no_puede_acceder_al_editor(as_admin):
    r = as_admin.post(
        "/api/v1/form-definitions/ingresos/draft",
        json={"fields": _campos_sistema()},
    )
    assert r.status_code == 403


def test_auditor_no_puede_acceder_al_editor(as_auditor):
    r = as_auditor.post(
        "/api/v1/form-definitions/ingresos/draft",
        json={"fields": _campos_sistema()},
    )
    assert r.status_code == 403


# CA-1: crear borrador, publicar, campo aparece en versión publicada
def test_crear_draft_y_publicar(as_coordinacion):
    # crear borrador
    r = as_coordinacion.post(
        "/api/v1/form-definitions/ingresos/draft",
        json={"fields": _campos_sistema()},
    )
    assert r.status_code == 201, r.text
    version_id = r.json()["id"]
    assert r.json()["status"] == "draft"

    # publicar
    pub = as_coordinacion.post(f"/api/v1/form-definitions/ingresos/publish/{version_id}")
    assert pub.status_code == 200, pub.text
    assert pub.json()["success"] is True

    # la versión publicada es visible
    get = as_coordinacion.get("/api/v1/form-definitions/ingresos/published")
    assert get.status_code == 200
    keys = [f["field_key"] for f in get.json()["fields"]]
    assert "sexo" in keys
    assert "diagnostico" in keys


# CA-3: guardar borrador no afecta la versión publicada
def test_borrador_no_afecta_publicado(as_coordinacion):
    # publicar versión base
    r1 = as_coordinacion.post(
        "/api/v1/form-definitions/modulo_x/draft",
        json={"fields": _campos_sistema()},
    )
    assert r1.status_code == 201
    vid1 = r1.json()["id"]
    as_coordinacion.post(f"/api/v1/form-definitions/modulo_x/publish/{vid1}")

    # crear nuevo borrador con campo extra
    campos2 = _campos_sistema() + [
        {"field_key": "observaciones", "label": "Observaciones", "field_type": "text",
         "required": False, "system_locked": False, "domain_values": None, "display_order": 8}
    ]
    r2 = as_coordinacion.post(
        "/api/v1/form-definitions/modulo_x/draft",
        json={"fields": campos2},
    )
    assert r2.status_code == 201

    # publicado sigue siendo la versión anterior
    pub = as_coordinacion.get("/api/v1/form-definitions/modulo_x/published")
    keys = [f["field_key"] for f in pub.json()["fields"]]
    assert "observaciones" not in keys


# TC-110-03 / CEPA-111 CA-1: publicar con campo sin tipo → bloqueado con errores
def test_publicar_formulario_mal_parametrizado_falla(as_coordinacion):
    campos_malos = _campos_sistema() + [
        {"field_key": "extra", "label": "Extra", "field_type": "",
         "required": False, "system_locked": False, "domain_values": None, "display_order": 9}
    ]
    r = as_coordinacion.post(
        "/api/v1/form-definitions/modulo_bad/draft",
        json={"fields": campos_malos},
    )
    assert r.status_code == 201
    vid = r.json()["id"]

    pub = as_coordinacion.post(f"/api/v1/form-definitions/modulo_bad/publish/{vid}")
    assert pub.status_code == 422
    assert pub.json()["success"] is False
    assert len(pub.json()["errors"]) >= 1


# TC-111-03 / CEPA-111 CA-2: quitar campo obligatorio del sistema → bloqueado
def test_no_se_puede_publicar_sin_campo_sistema(as_coordinacion):
    sin_diagnostico = [c for c in _campos_sistema() if c["field_key"] != "diagnostico"]
    r = as_coordinacion.post(
        "/api/v1/form-definitions/modulo_nd/draft",
        json={"fields": sin_diagnostico},
    )
    assert r.status_code == 201
    vid = r.json()["id"]

    pub = as_coordinacion.post(f"/api/v1/form-definitions/modulo_nd/publish/{vid}")
    assert pub.status_code == 422
    assert any("diagnostico" in e["error"] for e in pub.json()["errors"])


# TC-110-02: campo desactivado en nueva versión → histórico conservado
def test_campo_desactivado_nueva_version(as_coordinacion):
    # publicar v1 con campo "observaciones"
    campos1 = _campos_sistema() + [
        {"field_key": "observaciones", "label": "Obs", "field_type": "text",
         "required": False, "system_locked": False, "domain_values": None, "display_order": 8}
    ]
    r1 = as_coordinacion.post(
        "/api/v1/form-definitions/modulo_v/draft", json={"fields": campos1}
    )
    vid1 = r1.json()["id"]
    as_coordinacion.post(f"/api/v1/form-definitions/modulo_v/publish/{vid1}")

    # publicar v2 con "observaciones" desactivado
    campos2 = _campos_sistema() + [
        {"field_key": "observaciones", "label": "Obs", "field_type": "text",
         "required": False, "system_locked": False, "domain_values": None,
         "display_order": 8, "active": False}
    ]
    r2 = as_coordinacion.post(
        "/api/v1/form-definitions/modulo_v/draft", json={"fields": campos2}
    )
    vid2 = r2.json()["id"]
    pub2 = as_coordinacion.post(f"/api/v1/form-definitions/modulo_v/publish/{vid2}")
    assert pub2.json()["success"] is True

    # v1 sigue teniendo el campo activo (datos históricos conservados)
    get_v1 = as_coordinacion.get(f"/api/v1/form-definitions/modulo_v/versions/{vid1}")
    keys_v1 = [f["field_key"] for f in get_v1.json()["fields"]]
    assert "observaciones" in keys_v1
    obs_v1 = next(f for f in get_v1.json()["fields"] if f["field_key"] == "observaciones")
    assert obs_v1["active"] is True  # v1 no fue modificado

    # versión publicada actual (v2) tiene observaciones inactivo
    pub_now = as_coordinacion.get("/api/v1/form-definitions/modulo_v/published")
    obs_v2 = next(f for f in pub_now.json()["fields"] if f["field_key"] == "observaciones")
    assert obs_v2["active"] is False


# F1 — CEPA-111 RN-5: publicación bloqueada registra auditoría
def test_publicar_bloqueado_registra_auditoria(as_coordinacion, db_session: Session):
    """F1: un publish bloqueado (422) debe dejar una fila en audit_log con
    entity='form_version_publish_blocked'."""
    from sqlalchemy import select

    campos_malos = _campos_sistema() + [
        {"field_key": "extra_audit", "label": "Extra", "field_type": "",
         "required": False, "system_locked": False, "domain_values": None, "display_order": 9}
    ]
    r = as_coordinacion.post(
        "/api/v1/form-definitions/modulo_audit_test/draft",
        json={"fields": campos_malos},
    )
    assert r.status_code == 201
    vid = r.json()["id"]

    pub = as_coordinacion.post(f"/api/v1/form-definitions/modulo_audit_test/publish/{vid}")
    assert pub.status_code == 422

    log = db_session.scalars(
        select(AuditLog).where(
            AuditLog.entity == "form_version_publish_blocked",
            AuditLog.entity_id == str(vid),
            AuditLog.action == "UPDATE",
        )
    ).first()
    assert log is not None, "Se esperaba un AuditLog para la publicación bloqueada"


# TC-110-05 / TC-111-06: Auditor solo lectura en endpoints de escritura → 403
def test_auditor_solo_lectura_en_formularios(as_auditor, as_coordinacion):
    # coordinacion crea y publica primero
    r = as_coordinacion.post(
        "/api/v1/form-definitions/readonly_test/draft",
        json={"fields": _campos_sistema()},
    )
    vid = r.json()["id"]
    as_coordinacion.post(f"/api/v1/form-definitions/readonly_test/publish/{vid}")

    # auditor puede leer
    get = as_auditor.get("/api/v1/form-definitions/readonly_test/published")
    assert get.status_code == 200

    # auditor no puede escribir
    w = as_auditor.post(
        "/api/v1/form-definitions/readonly_test/draft",
        json={"fields": _campos_sistema()},
    )
    assert w.status_code == 403
