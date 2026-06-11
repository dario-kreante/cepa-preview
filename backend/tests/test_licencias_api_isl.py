def _make_ingreso_y_lm(as_admin, folio="F-ISL-001", rut="12.345.678-5"):
    r_ing = as_admin.post(
        "/api/v1/ingresos",
        json={
            "rut": rut,
            "nombre": "Paciente ISL",
            "sexo": "M",
            "edad": 45,
            "region": "Maule",
            "diagnostico": "Z57.1",
            "tipo_derivacion": "DIAT",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-01-15",
            "folio": folio,
        },
    )
    assert r_ing.status_code == 201, r_ing.text
    ing_id = r_ing.json()["id"]
    r_lm = as_admin.post(
        "/api/v1/licencias",
        json={
            "ingreso_id": ing_id,
            "tipo_lm": "5",
            "tipo_reposo": "total",
            "fecha_inicio": "2026-06-01",
            "fecha_termino": "2026-06-15",
            "fecha_emision": "2026-05-30",
            "inicio_reposo": "2026-06-01",
            "fin_reposo": "2026-06-15",
            "cantidad_dias": 15,
            "diagnostico": "Z57.1",
        },
    )
    assert r_lm.status_code == 201, r_lm.text
    return ing_id, r_lm.json()["id"]


# TC-073-01: marcar envío a ISL = enviado con fecha -> visible en historial
def test_marcar_envio_isl_enviado(as_admin):
    ing_id, lm_id = _make_ingreso_y_lm(as_admin)
    r = as_admin.patch(
        f"/api/v1/licencias/{lm_id}/isl",
        json={"envio_isl": "enviado", "fecha_envio_isl": "2026-06-02"},
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["envio_isl"] == "enviado"
    assert cuerpo["fecha_envio_isl"] == "2026-06-02"

    hist = as_admin.get(f"/api/v1/ingresos/{ing_id}/licencias")
    lm_en_hist = next(lm for lm in hist.json() if lm["id"] == lm_id)
    assert lm_en_hist["envio_isl"] == "enviado"


# TC-073-02: estado=enviado sin fecha -> 422
def test_isl_enviado_sin_fecha_422(as_admin):
    _, lm_id = _make_ingreso_y_lm(as_admin, folio="F-ISL-002", rut="7.876.543-7")
    r = as_admin.patch(
        f"/api/v1/licencias/{lm_id}/isl",
        json={"envio_isl": "enviado"},
    )
    assert r.status_code == 422


# TC-073-03: LM extra-sistema aparece en historial marcada y suma al acumulado
def test_extra_sistema_en_historial_y_acumulado(as_admin):
    r_ing = as_admin.post(
        "/api/v1/ingresos",
        json={
            "rut": "15.111.222-6",
            "nombre": "Extra Sistema Test",
            "sexo": "F",
            "edad": 32,
            "region": "Biobio",
            "diagnostico": "F41",
            "tipo_derivacion": "DIEP",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-02-01",
            "folio": "F-ISL-003",
        },
    )
    assert r_ing.status_code == 201, r_ing.text
    ing_id = r_ing.json()["id"]

    # LM en sistema
    as_admin.post(
        "/api/v1/licencias",
        json={
            "ingreso_id": ing_id,
            "tipo_lm": "1",
            "tipo_reposo": "total",
            "fecha_inicio": "2026-03-01",
            "fecha_termino": "2026-03-10",
            "fecha_emision": "2026-02-28",
            "inicio_reposo": "2026-03-01",
            "fin_reposo": "2026-03-10",
            "cantidad_dias": 10,
            "diagnostico": "F41",
        },
    )
    # LM extra-sistema
    as_admin.post(
        "/api/v1/licencias",
        json={
            "ingreso_id": ing_id,
            "tipo_lm": "1",
            "tipo_reposo": "parcial",
            "fecha_inicio": "2026-04-01",
            "fecha_termino": "2026-04-20",
            "fecha_emision": "2026-03-30",
            "inicio_reposo": "2026-04-01",
            "fin_reposo": "2026-04-20",
            "cantidad_dias": 20,
            "diagnostico": "F41",
            "origen": "extra_sistema",
        },
    )

    hist = as_admin.get(f"/api/v1/ingresos/{ing_id}/licencias")
    origenes = [lm["origen"] for lm in hist.json()]
    assert "extra_sistema" in origenes

    acum = as_admin.get(f"/api/v1/ingresos/{ing_id}/licencias/acumulado")
    assert acum.status_code == 200
    assert acum.json()["dias_acumulados_vigentes"] == 30
    assert acum.json()["incluye_extra_sistema"] is True


# TC-073-04: 77 BIS (rechazo ISL + anulación) excluye del acumulado
def test_77bis_excluye_del_acumulado(as_admin):
    r_ing = as_admin.post(
        "/api/v1/ingresos",
        json={
            "rut": "11.222.333-9",
            "nombre": "77BIS Test",
            "sexo": "M",
            "edad": 50,
            "region": "Maule",
            "diagnostico": "Z57.5",
            "tipo_derivacion": "DIAT",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-01-01",
            "folio": "F-ISL-004",
        },
    )
    ing_id = r_ing.json()["id"]
    lm_id = as_admin.post(
        "/api/v1/licencias",
        json={
            "ingreso_id": ing_id,
            "tipo_lm": "5",
            "tipo_reposo": "total",
            "fecha_inicio": "2026-02-01",
            "fecha_termino": "2026-02-15",
            "fecha_emision": "2026-01-30",
            "inicio_reposo": "2026-02-01",
            "fin_reposo": "2026-02-15",
            "cantidad_dias": 15,
            "diagnostico": "Z57.5",
        },
    ).json()["id"]

    # Marcar como rechazada por ISL
    as_admin.patch(
        f"/api/v1/licencias/{lm_id}/isl",
        json={"envio_isl": "rechazado", "fecha_envio_isl": "2026-02-20",
              "observaciones": "Rechazada 77 BIS"},
    )
    # Anular la LM
    as_admin.patch(
        f"/api/v1/licencias/{lm_id}/anular",
        json={"observaciones": "77 BIS — reclasificada como enfermedad común"},
    )

    acum = as_admin.get(f"/api/v1/ingresos/{ing_id}/licencias/acumulado")
    assert acum.json()["dias_acumulados_vigentes"] == 0


# TC-073-05: EEAG fuera de rango -> 422
def test_eeag_fuera_de_rango_422(as_admin):
    _, lm_id = _make_ingreso_y_lm(as_admin, folio="F-ISL-005", rut="16.555.666-6")
    r = as_admin.patch(
        f"/api/v1/licencias/{lm_id}/isl",
        json={"envio_isl": "enviado", "fecha_envio_isl": "2026-06-05", "eeag_gaf": 150},
    )
    assert r.status_code == 422


# TC-073-06: Auditor no puede editar ISL -> 403
def test_auditor_no_puede_editar_isl(as_admin, as_auditor):
    _, lm_id = _make_ingreso_y_lm(as_admin, folio="F-ISL-006", rut="18.777.888-3")
    r = as_auditor.patch(
        f"/api/v1/licencias/{lm_id}/isl",
        json={"envio_isl": "enviado", "fecha_envio_isl": "2026-06-05"},
    )
    assert r.status_code == 403


# CA-4 CEPA-073: Auditor puede leer historial con trazabilidad ISL
def test_auditor_puede_leer_historial_con_isl(as_admin, as_auditor):
    ing_id, lm_id = _make_ingreso_y_lm(as_admin, folio="F-ISL-007", rut="19.888.999-7")
    as_admin.patch(
        f"/api/v1/licencias/{lm_id}/isl",
        json={"envio_isl": "enviado", "fecha_envio_isl": "2026-06-03"},
    )
    r = as_auditor.get(f"/api/v1/ingresos/{ing_id}/licencias")
    assert r.status_code == 200
    assert r.json()[0]["envio_isl"] == "enviado"
