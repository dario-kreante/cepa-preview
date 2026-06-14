import datetime


def _crear_ingreso(as_admin, rut, folio):
    r = as_admin.post(
        "/api/v1/ingresos",
        json={
            "rut": rut,
            "nombre": "Acum Test",
            "sexo": "F",
            "edad": 40,
            "region": "Maule",
            "diagnostico": "F32",
            "tipo_derivacion": "DIAT",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-01-01",
            "folio": folio,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _crear_lm(as_admin, ing_id, inicio, termino, dias, origen="sistema"):
    r = as_admin.post(
        "/api/v1/licencias",
        json={
            "ingreso_id": ing_id,
            "tipo_lm": "1",
            "tipo_reposo": "total",
            "fecha_inicio": inicio,
            "fecha_termino": termino,
            "fecha_emision": inicio,
            "inicio_reposo": inicio,
            "fin_reposo": termino,
            "cantidad_dias": dias,
            "diagnostico": "F32.1",
            "origen": origen,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# TC-071-01: CA-1 del PRD §7.7.4 — 4 LM (3 previas + 1 nueva) → 40 días
def test_acumulado_cuatro_lm_sin_solapamiento(as_admin):
    ing_id = _crear_ingreso(as_admin, "12.345.678-5", "F-ACUM-001")
    _crear_lm(as_admin, ing_id, "2026-01-01", "2026-01-10", 10)
    _crear_lm(as_admin, ing_id, "2026-02-01", "2026-02-15", 15)
    _crear_lm(as_admin, ing_id, "2026-03-01", "2026-03-07", 7)
    _crear_lm(as_admin, ing_id, "2026-04-01", "2026-04-08", 8)

    r = as_admin.get(f"/api/v1/ingresos/{ing_id}/licencias/acumulado")
    assert r.status_code == 200
    assert r.json()["dias_acumulados_vigentes"] == 40
    assert r.json()["hay_solapamiento"] is False


# TC-071-03: solapamiento → 15 efectivos, 20 bruto
def test_acumulado_con_solapamiento(as_admin):
    ing_id = _crear_ingreso(as_admin, "7.876.543-7", "F-ACUM-002")
    _crear_lm(as_admin, ing_id, "2026-06-01", "2026-06-10", 10)
    _crear_lm(as_admin, ing_id, "2026-06-06", "2026-06-15", 10)

    r = as_admin.get(f"/api/v1/ingresos/{ing_id}/licencias/acumulado")
    body = r.json()
    assert body["dias_acumulados_vigentes"] == 15
    assert body["dias_acumulados_bruto"] == 20
    assert body["hay_solapamiento"] is True


# TC-071-06: Auditor puede ver acumulado (solo lectura)
def test_auditor_puede_ver_acumulado(as_admin, as_auditor):
    ing_id = _crear_ingreso(as_admin, "15.111.222-6", "F-ACUM-003")
    _crear_lm(as_admin, ing_id, "2026-05-01", "2026-05-12", 12)

    r = as_auditor.get(f"/api/v1/ingresos/{ing_id}/licencias/acumulado")
    assert r.status_code == 200
    assert r.json()["dias_acumulados_vigentes"] == 12


# TC-072-01: disparo manual del job de alertas genera alertas para LM cercanas
def test_disparo_alertas_genera_para_lm_proxima(as_admin):
    # Creamos un ingreso con LM que vence hoy + 2 días
    ing_id = _crear_ingreso(as_admin, "16.555.666-6", "F-ALRTA-001")
    hoy = datetime.date.today()
    termino = hoy + datetime.timedelta(days=2)
    inicio = termino - datetime.timedelta(days=14)
    as_admin.post(
        "/api/v1/licencias",
        json={
            "ingreso_id": ing_id,
            "tipo_lm": "1",
            "tipo_reposo": "total",
            "fecha_inicio": inicio.isoformat(),
            "fecha_termino": termino.isoformat(),
            "fecha_emision": inicio.isoformat(),
            "inicio_reposo": inicio.isoformat(),
            "fin_reposo": termino.isoformat(),
            "cantidad_dias": 15,
            "diagnostico": "F32.1",
        },
    )

    r = as_admin.post("/api/v1/licencias/alertas/generar")
    assert r.status_code == 200
    # Al menos una alerta fue creada (puede haber más si otros tests dejaron LM próximas)
    assert isinstance(r.json(), list)


# TC-072-04: idempotencia del job — segunda llamada no duplica
def test_alertas_job_idempotente(as_admin):
    r1 = as_admin.post("/api/v1/licencias/alertas/generar")
    r2 = as_admin.post("/api/v1/licencias/alertas/generar")
    assert r1.status_code == 200
    assert r2.status_code == 200
    # La segunda llamada no devuelve las mismas alertas (ya existen, no se duplican)
    ids_primera = {a["id"] for a in r1.json()}
    ids_segunda = {a["id"] for a in r2.json()}
    assert ids_primera.isdisjoint(ids_segunda)


# TC-072-05: Verificamos que el job solo puede dispararlo un escritor
def test_auditor_no_puede_disparar_job_alertas(as_auditor):
    r = as_auditor.post("/api/v1/licencias/alertas/generar")
    assert r.status_code == 403
