"""Tests — Task 9 EPIC-09: Ventanas de proceso CEPA-096."""
import pytest


# ── TC-096-01: lista de ventanas de proceso disponibles ──────────────────────

def test_listar_ventanas_proceso(as_coordinacion):
    resp = as_coordinacion.get("/api/v1/ventanas-proceso")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)


# ── TC-096-03: los cinco tipos de proceso existen o se pueden crear ──────────

PROCESOS_REQUERIDOS = ["licencias", "farmacos", "auditoria", "reintegro", "controles"]


def test_crear_y_listar_ventana_por_proceso(as_coordinacion):
    for proceso in PROCESOS_REQUERIDOS:
        resp = as_coordinacion.post("/api/v1/ventanas-proceso", json={
            "proceso": proceso,
            "columnas_visibles": ["id", "estado", "fecha"],
            "orden_por_defecto": "fecha",
        })
        assert resp.status_code == 201, f"Falló para proceso: {proceso}"

    resp = as_coordinacion.get("/api/v1/ventanas-proceso")
    assert resp.status_code == 200
    procesos_creados = [v["proceso"] for v in resp.json()]
    for p in PROCESOS_REQUERIDOS:
        assert p in procesos_creados


# ── TC-096-04: proceso vacío devuelve lista vacía, sin error ─────────────────

def test_ventana_proceso_lista_vacia_sin_error(as_coordinacion):
    resp = as_coordinacion.get("/api/v1/ventanas-proceso", params={"proceso": "INEXISTENTE_ZZZ"})
    assert resp.status_code == 200
    assert resp.json() == []


# ── TC-096-05: Auditor solo lectura ──────────────────────────────────────────

def test_ventana_proceso_auditor_solo_lectura(as_auditor):
    resp_get = as_auditor.get("/api/v1/ventanas-proceso")
    assert resp_get.status_code == 200

    resp_post = as_auditor.post("/api/v1/ventanas-proceso", json={
        "proceso": "licencias",
        "columnas_visibles": ["id"],
    })
    assert resp_post.status_code == 403


def test_ventana_proceso_sin_auth(client):
    resp = client.get("/api/v1/ventanas-proceso")
    assert resp.status_code == 401
