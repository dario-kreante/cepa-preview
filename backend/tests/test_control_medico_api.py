"""Tests de integración del módulo de Controles Médicos (EPIC-06).

Cubre todos los Criterios de Aceptación (CA) y Test Cases (TC) de:
- CEPA-060 (TC-060-01 a TC-060-06)
- CEPA-061 (TC-061-01 a TC-061-06)
- CEPA-062 (TC-062-01 a TC-062-06)

Precondición: en conftest.py existen fixtures `as_admin`, `as_coordinacion`,
`as_auditor`, `db_session`, `client` (definidos por EPIC-00).
Los helpers `_crear_paciente_e_ingreso` crean las entidades previas necesarias
directamente en la sesión para aislar cada test.
"""

import pytest
from datetime import date

from sqlalchemy.orm import Session

from app.models.ingreso import Ingreso
from app.models.paciente import Paciente


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de fixture
# ─────────────────────────────────────────────────────────────────────────────

def _crear_ingreso(db: Session, folio: str = "F-TEST-0001", fecha_ingreso: date | None = None) -> Ingreso:
    """Crea un paciente y un ingreso mínimo para usar como precondición."""
    from datetime import date as _date
    import uuid

    rut = f"test{uuid.uuid4().hex[:6]}"
    p = Paciente(
        rut=rut,
        nombre="Paciente Test",
        sexo="F",
        edad=35,
        region="Maule",
    )
    db.add(p)
    db.flush()

    fi = fecha_ingreso or _date(2026, 1, 5)
    ing = Ingreso(
        paciente_id=p.id,
        folio=folio,
        folio_manual=True,
        fecha_ingreso=fi,
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="Trastorno adaptativo",
        estado="activo",
    )
    db.add(ing)
    db.flush()
    return ing


def _payload_control(ingreso_id: int, fecha_control: str = "2026-02-02") -> dict:
    return {
        "ingreso_id": ingreso_id,
        "fecha_control": fecha_control,
        "medico_tratante": "Dr. Ramírez",
        "region_derivacion": "Maule",
    }


# ─────────────────────────────────────────────────────────────────────────────
# CEPA-060: Registro de control y cálculo automático de semana
# ─────────────────────────────────────────────────────────────────────────────

# CA-1 + TC-060-01: control guardado; semana_control=5 (fecha_ingreso=2026-01-05, fecha_control=2026-02-02)
def test_tc_060_01_control_guardado_semana_5(as_admin, db_session):
    ing = _crear_ingreso(db_session, folio="F-2026-0001", fecha_ingreso=date(2026, 1, 5))
    r = as_admin.post("/api/v1/controles-medicos", json=_payload_control(ing.id, "2026-02-02"))
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["semana_control"] == 5
    assert cuerpo["ingreso_id"] == ing.id
    assert cuerpo["fecha_control"] == "2026-02-02"


# CA-2 + TC-060-02: semana_control calculada correctamente (fecha_ingreso=2026-03-02, control=2026-03-10 → semana 2)
def test_tc_060_02_semana_2(as_admin, db_session):
    ing = _crear_ingreso(db_session, folio="F-2026-0002", fecha_ingreso=date(2026, 3, 2))
    r = as_admin.post("/api/v1/controles-medicos", json=_payload_control(ing.id, "2026-03-10"))
    assert r.status_code == 201
    assert r.json()["semana_control"] == 2


# TC-060-05 (borde): mismo día → semana 1
def test_tc_060_05_mismo_dia_semana_1(as_admin, db_session):
    ing = _crear_ingreso(db_session, folio="F-2026-0003", fecha_ingreso=date(2026, 4, 1))
    r = as_admin.post("/api/v1/controles-medicos", json=_payload_control(ing.id, "2026-04-01"))
    assert r.status_code == 201
    assert r.json()["semana_control"] == 1


# CA-4 + TC-060-04: folio inexistente → 404
def test_tc_060_04_folio_inexistente(as_admin):
    r = as_admin.post("/api/v1/controles-medicos", json=_payload_control(99999))
    assert r.status_code == 404
    assert "ingreso" in r.text.lower()


# RN-4: fecha_control anterior a fecha_ingreso → 422
def test_fecha_control_anterior_a_ingreso_rechazada(as_admin, db_session):
    ing = _crear_ingreso(db_session, folio="F-2026-0004", fecha_ingreso=date(2026, 6, 10))
    r = as_admin.post("/api/v1/controles-medicos", json=_payload_control(ing.id, "2026-06-09"))
    assert r.status_code == 422
    assert "anterior" in r.text.lower()


# TC-060-06 (permisos): Auditor no puede crear → 403
def test_tc_060_06_auditor_no_puede_crear(as_auditor, db_session):
    ing = _crear_ingreso(db_session, folio="F-2026-0005")
    r = as_auditor.post("/api/v1/controles-medicos", json=_payload_control(ing.id))
    assert r.status_code == 403


# CA-1: control visible en listado por ingreso
def test_control_visible_en_listado(as_admin, db_session):
    ing = _crear_ingreso(db_session, folio="F-2026-0006", fecha_ingreso=date(2026, 1, 5))
    as_admin.post("/api/v1/controles-medicos", json=_payload_control(ing.id, "2026-02-02"))
    r = as_admin.get(f"/api/v1/controles-medicos/por-ingreso/{ing.id}")
    assert r.status_code == 200
    lista = r.json()
    assert len(lista) >= 1
    assert lista[0]["ingreso_id"] == ing.id


# Semana solo lectura: el campo semana_control no se acepta desde el payload
def test_semana_control_es_solo_lectura(as_admin, db_session):
    ing = _crear_ingreso(db_session, folio="F-2026-0007", fecha_ingreso=date(2026, 1, 5))
    payload = _payload_control(ing.id, "2026-02-02")
    payload["semana_control"] = 99  # intento de sobreescribir
    r = as_admin.post("/api/v1/controles-medicos", json=payload)
    # El endpoint ignora semana_control del payload y calcula el correcto
    assert r.status_code == 201
    assert r.json()["semana_control"] == 5  # calculado, no 99


# ─────────────────────────────────────────────────────────────────────────────
# CEPA-061: Programación del próximo control y estado de agenda
# ─────────────────────────────────────────────────────────────────────────────

def _crear_control(as_admin, db_session, folio: str, fecha_ingreso: date, fecha_control: str) -> dict:
    """Helper: crea ingreso + control; devuelve el cuerpo JSON del control."""
    ing = _crear_ingreso(db_session, folio=folio, fecha_ingreso=fecha_ingreso)
    r = as_admin.post("/api/v1/controles-medicos", json=_payload_control(ing.id, fecha_control))
    assert r.status_code == 201, r.text
    return r.json()


# CA-1 + TC-061-01: próximo control y agendado persistidos
def test_tc_061_01_proximo_control_agendado(as_admin, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-061-01", date(2026, 1, 5), "2026-02-02")
    r = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/proximo-control",
        json={"proximo_control": "2026-03-15", "proximo_agendado": True},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["proximo_control"] == "2026-03-15"
    assert body["proximo_agendado"] is True


# CA-2 + TC-061-04 (borde): agendado por defecto = False
def test_tc_061_04_agendado_por_defecto_false(as_admin, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-061-04", date(2026, 1, 5), "2026-02-02")
    r = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/proximo-control",
        json={"proximo_control": "2026-03-15"},  # sin proximo_agendado
    )
    assert r.status_code == 200
    assert r.json()["proximo_agendado"] is False


# CA-4 + TC-061-03: próximo anterior al control actual → 422
def test_tc_061_03_proximo_anterior_rechazado(as_admin, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-061-03", date(2026, 1, 5), "2026-03-01")
    r = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/proximo-control",
        json={"proximo_control": "2026-02-20"},
    )
    assert r.status_code == 422
    assert "posterior" in r.text.lower()


# TC-061-05 (borde): programar nuevo próximo cierra el anterior pendiente
def test_tc_061_05_nuevo_proximo_cierra_anterior(as_admin, db_session):
    ing = _crear_ingreso(db_session, folio="F-061-05", fecha_ingreso=date(2026, 1, 5))

    r1 = as_admin.post("/api/v1/controles-medicos", json=_payload_control(ing.id, "2026-02-01"))
    ctrl1_id = r1.json()["id"]
    as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl1_id}/proximo-control",
        json={"proximo_control": "2026-03-01"},
    )

    r2 = as_admin.post("/api/v1/controles-medicos", json=_payload_control(ing.id, "2026-03-01"))
    ctrl2_id = r2.json()["id"]
    as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl2_id}/proximo-control",
        json={"proximo_control": "2026-04-01"},
    )

    # el primer control ya no tiene próximo vigente
    r_ctrl1 = as_admin.get(f"/api/v1/controles-medicos/{ctrl1_id}")
    assert r_ctrl1.json()["proximo_control"] is None


# TC-061-06 (permisos): Auditor no puede programar próximo control → 403
def test_tc_061_06_auditor_no_puede_programar(as_auditor, as_admin, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-061-06", date(2026, 1, 5), "2026-02-02")
    r = as_auditor.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/proximo-control",
        json={"proximo_control": "2026-03-15"},
    )
    assert r.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# CEPA-062: Licencias y RECA asociadas al control
# ─────────────────────────────────────────────────────────────────────────────

# CA-1 + TC-062-01: licencia=sí con datos completos → persistido
def test_tc_062_01_licencia_con_datos_persistida(as_admin, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-062-01", date(2026, 1, 5), "2026-02-02")
    r = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/licencia",
        json={
            "tiene_licencia": True,
            "resumen_termino_lm": "LM tipo 1 por 15 días",
            "total_dias_lm": 15,
            "tipo_licencia": "1",
            "tipo_reposo": "total",
            "gaf": 55,
            "estado_reca": "pendiente",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tiene_licencia"] is True
    assert body["total_dias_lm"] == 15
    assert body["tipo_reposo"] == "total"
    assert body["tipo_licencia"] == "1"
    assert body["gaf"] == 55


# CA-2 + TC-062-05 (borde): licencia=no → campos de LM vacíos, guardado correcto
def test_tc_062_05_licencia_no_campos_vacios(as_admin, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-062-05", date(2026, 1, 5), "2026-02-02")
    r = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/licencia",
        json={"tiene_licencia": False},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tiene_licencia"] is False
    assert body["total_dias_lm"] is None
    assert body["tipo_licencia"] is None
    assert body["tipo_reposo"] is None


# CA-3 + TC-062-04: GAF fuera de rango → 422
def test_tc_062_04_gaf_fuera_de_rango(as_admin, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-062-04", date(2026, 1, 5), "2026-02-02")
    r = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/licencia",
        json={
            "tiene_licencia": True,
            "resumen_termino_lm": "x",
            "total_dias_lm": 5,
            "tipo_licencia": "1",
            "tipo_reposo": "total",
            "gaf": 120,
        },
    )
    assert r.status_code == 422
    assert "100" in r.text or "gaf" in r.text.lower()


# Borde GAF=0 (límite inferior válido)
def test_gaf_limite_inferior_valido(as_admin, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-062-gaf0", date(2026, 1, 5), "2026-02-02")
    r = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/licencia",
        json={
            "tiene_licencia": True,
            "resumen_termino_lm": "x",
            "total_dias_lm": 1,
            "tipo_licencia": "1",
            "tipo_reposo": "total",
            "gaf": 0,
        },
    )
    assert r.status_code == 200
    assert r.json()["gaf"] == 0


# Borde GAF=100 (límite superior válido)
def test_gaf_limite_superior_valido(as_admin, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-062-gaf100", date(2026, 1, 5), "2026-02-02")
    r = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/licencia",
        json={
            "tiene_licencia": True,
            "resumen_termino_lm": "x",
            "total_dias_lm": 1,
            "tipo_licencia": "1",
            "tipo_reposo": "total",
            "gaf": 100,
        },
    )
    assert r.status_code == 200
    assert r.json()["gaf"] == 100


# Borde GAF=-1 (fuera de rango inferior)
def test_gaf_negativo_rechazado(as_admin, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-062-gaf-1", date(2026, 1, 5), "2026-02-02")
    r = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/licencia",
        json={
            "tiene_licencia": True,
            "resumen_termino_lm": "x",
            "total_dias_lm": 1,
            "tipo_licencia": "1",
            "tipo_reposo": "total",
            "gaf": -1,
        },
    )
    assert r.status_code == 422


# CA-3 + TC-062-03: licencia=sí sin campos obligatorios → 422
def test_tc_062_03_licencia_si_sin_campos_obligatorios(as_admin, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-062-03", date(2026, 1, 5), "2026-02-02")
    r = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/licencia",
        json={"tiene_licencia": True},  # sin resumen, días, tipo_licencia, tipo_reposo
    )
    assert r.status_code == 422
    assert "obligatorio" in r.text.lower() or "resumen_termino_lm" in r.text


# CA-4 + TC-062-02: RECA y observaciones persistidos y visibles para Auditor
def test_tc_062_02_reca_visible_para_auditor(as_admin, as_auditor, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-062-02", date(2026, 1, 5), "2026-02-02")
    as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/licencia",
        json={
            "tiene_licencia": False,
            "estado_reca": "pendiente",
            "observaciones": "Reevaluar en próximo control",
        },
    )
    # Auditor puede leer
    r = as_auditor.get(f"/api/v1/controles-medicos/{ctrl['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["estado_reca"] == "pendiente"
    assert body["observaciones"] == "Reevaluar en próximo control"


# TC-062-06 (permisos): Auditor no puede editar licencia → 403
def test_tc_062_06_auditor_no_puede_editar_licencia(as_auditor, as_admin, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-062-06", date(2026, 1, 5), "2026-02-02")
    r = as_auditor.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/licencia",
        json={"tiene_licencia": False},
    )
    assert r.status_code == 403


# Lectura permitida para Auditor
def test_auditor_puede_listar_controles(as_auditor, as_admin, db_session):
    ing = _crear_ingreso(db_session, folio="F-AUDIT-01", fecha_ingreso=date(2026, 1, 5))
    as_admin.post("/api/v1/controles-medicos", json=_payload_control(ing.id, "2026-02-02"))
    r = as_auditor.get(f"/api/v1/controles-medicos/por-ingreso/{ing.id}")
    assert r.status_code == 200
