

def _payload_ingreso(as_admin, rut="12.345.678-5", folio="F-LIC-001"):
    """Crea un ingreso de prueba y devuelve su id."""
    r = as_admin.post(
        "/api/v1/ingresos",
        json={
            "rut": rut,
            "nombre": "Paciente Licencias",
            "sexo": "F",
            "edad": 38,
            "region": "Maule",
            "diagnostico": "F32.1",
            "tipo_derivacion": "DIAT",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-01-10",
            "folio": folio,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _payload_lm(ingreso_id, **over):
    base = {
        "ingreso_id": ingreso_id,
        "tipo_lm": "1",
        "tipo_reposo": "total",
        "fecha_inicio": "2026-06-01",
        "fecha_termino": "2026-06-15",
        "fecha_emision": "2026-05-30",
        "inicio_reposo": "2026-06-01",
        "fin_reposo": "2026-06-15",
        "cantidad_dias": 15,
        "diagnostico": "F32.1",
    }
    base.update(over)
    return base


# TC-070-01: registro exitoso, vinculado al ingreso, visible en historial
def test_crear_lm_registra_y_aparece_en_historial(as_admin):
    ing_id = _payload_ingreso(as_admin)
    r = as_admin.post("/api/v1/licencias", json=_payload_lm(ing_id))
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["ingreso_id"] == ing_id
    assert cuerpo["tipo_lm"] == "1"
    assert cuerpo["anulada"] is False

    hist = as_admin.get(f"/api/v1/ingresos/{ing_id}/licencias")
    assert hist.status_code == 200
    ids = [lm["id"] for lm in hist.json()]
    assert cuerpo["id"] in ids


# TC-070-02: fecha_termino < fecha_inicio -> 422
def test_fecha_termino_anterior_rechaza_422(as_admin):
    ing_id = _payload_ingreso(as_admin, folio="F-LIC-002")
    r = as_admin.post(
        "/api/v1/licencias",
        json=_payload_lm(ing_id, fecha_inicio="2026-06-15", fecha_termino="2026-06-01"),
    )
    assert r.status_code == 422


# TC-070-03: RUT con DV inválido al crear ingreso -> 422 (ya cubierto en EPIC-01; aquí
# verificamos que la LM requiere ingreso existente)
def test_ingreso_inexistente_rechaza_404(as_admin):
    r = as_admin.post("/api/v1/licencias", json=_payload_lm(99999))
    assert r.status_code == 404


# TC-070-04: inconsistencia cantidad_dias vs. fechas genera advertencia (campo en respuesta)
def test_inconsistencia_dias_vs_fechas_genera_advertencia(as_admin):
    ing_id = _payload_ingreso(as_admin, folio="F-LIC-004")
    # 15 días declarados pero fin-inicio+1 = 12
    r = as_admin.post(
        "/api/v1/licencias",
        json=_payload_lm(
            ing_id,
            fecha_inicio="2026-06-01",
            fecha_termino="2026-06-12",
            inicio_reposo="2026-06-01",
            fin_reposo="2026-06-12",
            cantidad_dias=15,
        ),
    )
    # la advertencia no bloquea; se guarda con advertencia en el cuerpo
    assert r.status_code == 201
    assert r.json().get("advertencia_dias") is not None


# TC-070-05: tipo_lm fuera de {1,5,6} -> 422
def test_tipo_lm_invalido_422(as_admin):
    ing_id = _payload_ingreso(as_admin, folio="F-LIC-005")
    r = as_admin.post("/api/v1/licencias", json=_payload_lm(ing_id, tipo_lm="3"))
    assert r.status_code == 422


# TC-070-06: Auditor no puede crear -> 403
def test_auditor_no_puede_crear_lm(as_auditor):
    r = as_auditor.post("/api/v1/licencias", json=_payload_lm(1))
    assert r.status_code == 403


# Auditor puede leer historial -> 200
def test_auditor_puede_leer_historial(as_admin, as_auditor):
    ing_id = _payload_ingreso(as_admin, rut="7.876.543-7", folio="F-LIC-006")
    as_admin.post("/api/v1/licencias", json=_payload_lm(ing_id))
    r = as_auditor.get(f"/api/v1/ingresos/{ing_id}/licencias")
    assert r.status_code == 200


# Anulación (77 BIS): PATCH /licencias/{id}/anular
def test_anular_lm_cambia_campo_anulada(as_admin):
    ing_id = _payload_ingreso(as_admin, folio="F-LIC-007")
    lm_id = as_admin.post("/api/v1/licencias", json=_payload_lm(ing_id)).json()["id"]
    r = as_admin.patch(
        f"/api/v1/licencias/{lm_id}/anular",
        json={"observaciones": "Rechazada por 77 BIS"},
    )
    assert r.status_code == 200
    assert r.json()["anulada"] is True


# Auditor no puede anular -> 403
def test_auditor_no_puede_anular(as_admin, as_auditor):
    ing_id = _payload_ingreso(as_admin, folio="F-LIC-008")
    lm_id = as_admin.post("/api/v1/licencias", json=_payload_lm(ing_id)).json()["id"]
    r = as_auditor.patch(
        f"/api/v1/licencias/{lm_id}/anular",
        json={"observaciones": "intento de anulación"},
    )
    assert r.status_code == 403
