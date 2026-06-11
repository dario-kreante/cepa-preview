def _ingreso(as_admin, **over):
    base = {
        "rut": "11.111.111-1",
        "nombre": "Ana González",
        "sexo": "F",
        "edad": 33,
        "region": "Maule",
        "diagnostico": "x",
        "tipo_derivacion": "DIAT",
        "tipo_ingreso": "convenio",
        "modelo_tratamiento": "ambulatorio",
        "fecha_ingreso": "2026-06-01",
    }
    base.update(over)
    return as_admin.post("/api/v1/ingresos", json=base).json()


def _set_plazo(db_session, programa="PROG-A", dias=10):
    from app.models.plazo_programa import PlazoPrograma

    db_session.merge(PlazoPrograma(programa=programa, dias_plazo_informe=dias))
    db_session.commit()


# TC-013-01: acogida + consentimiento (estado de consentimiento vive en CEPA-016; aquí acogida)
def test_registrar_acogida(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.put(
        f"/api/v1/ingresos/{ing['id']}/seguimiento",
        json={"fecha_acogida": "2026-06-02", "programa": "PROG-A"},
    )
    assert r.status_code == 200
    assert r.json()["fecha_acogida"] == "2026-06-02"


# TC-013-02: evaluaciones con estados
def test_registrar_evaluaciones(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.put(
        f"/api/v1/ingresos/{ing['id']}/seguimiento",
        json={
            "programa": "PROG-A",
            "eval_medica_estado": "realizada",
            "eval_medica_medico": "Dr. Soto",
            "eval_medica_fecha": "2026-06-05",
            "eval_psico_estado": "pendiente",
        },
    )
    assert r.status_code == 200
    assert r.json()["eval_medica_estado"] == "realizada"


# TC-013-03: evaluación dentro de plazo -> validador "en_plazo"
def test_validador_en_plazo(as_admin, db_session):
    _set_plazo(db_session, "PROG-A", dias=10)
    ing = _ingreso(as_admin, fecha_ingreso="2026-06-01")
    as_admin.put(
        f"/api/v1/ingresos/{ing['id']}/seguimiento",
        json={"programa": "PROG-A", "eval_medica_estado": "realizada", "eval_medica_fecha": "2026-06-05"},
    )
    r = as_admin.get(f"/api/v1/ingresos/{ing['id']}/seguimiento/validacion-plazo")
    assert r.status_code == 200
    assert r.json()["cumplimiento"] == "en_plazo"


# TC-013-04: evaluación fuera de plazo -> "fuera_de_plazo"
def test_validador_fuera_de_plazo(as_admin, db_session):
    _set_plazo(db_session, "PROG-B", dias=3)
    ing = _ingreso(as_admin, rut="7.876.543-7", fecha_ingreso="2026-06-01")
    as_admin.put(
        f"/api/v1/ingresos/{ing['id']}/seguimiento",
        json={"programa": "PROG-B", "eval_medica_estado": "realizada", "eval_medica_fecha": "2026-06-20"},
    )
    r = as_admin.get(f"/api/v1/ingresos/{ing['id']}/seguimiento/validacion-plazo")
    assert r.json()["cumplimiento"] == "fuera_de_plazo"


# TC-013-05: estado "no_aplica" no exige médico/diagnóstico
def test_no_aplica_sin_medico(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.put(
        f"/api/v1/ingresos/{ing['id']}/seguimiento",
        json={"eval_medica_estado": "no_aplica"},
    )
    assert r.status_code == 200


# borde: estado de evaluación inválido -> 422
def test_estado_evaluacion_invalido(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.put(
        f"/api/v1/ingresos/{ing['id']}/seguimiento",
        json={"eval_medica_estado": "quizas"},
    )
    assert r.status_code == 422


# TC-013-06: Auditor no puede editar seguimiento -> 403
def test_auditor_no_edita_seguimiento(as_admin, as_auditor):
    ing = _ingreso(as_admin)
    r = as_auditor.put(
        f"/api/v1/ingresos/{ing['id']}/seguimiento", json={"fecha_acogida": "2026-06-02"}
    )
    assert r.status_code == 403
