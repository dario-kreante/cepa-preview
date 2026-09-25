"""Tramos de GAF (COMP-2609-12, v5 D18) y alerta por tramo en licencia (COMP-2609-20).

El catálogo ``gaf_tramo`` se siembra con los 10 tramos EEAG de 10 en 10, provisorios hasta
que Pilar confirme la segmentación (PA-v5-03). La alerta por tramo se siembra desactivada:
sin criterio de la contraparte no se inventa uno (CEPA-075 RN-2).
"""

import datetime
import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.domain.gaf import TRAMOS_EEAG, Tramo, tramo_que_contiene
from app.models.alertas import AlertaNotif
from app.models.config_alerta import ConfigAlerta
from app.models.control_medico import ControlMedico
from app.models.gaf_tramo import GafTramo
from app.models.ingreso import Ingreso
from app.models.licencia import LicenciaMedica
from app.models.paciente import Paciente
from app.services.alertas import ejecutar_job_alertas

HOY = datetime.date(2026, 10, 5)


def _ingreso(db: Session, sufijo: str) -> Ingreso:
    pac = Paciente(rut=f"88{sufijo}", nombre="Paciente GAF", sexo="F", edad=40, region="Maule")
    db.add(pac)
    db.flush()
    ing = Ingreso(
        paciente_id=pac.id,
        folio=f"F-GAF-{sufijo}",
        folio_manual=True,
        fecha_ingreso=datetime.date(2026, 1, 5),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="F32",
        estado="activo",
    )
    db.add(ing)
    db.flush()
    return ing


def _licencia(
    db: Session,
    sufijo: str,
    *,
    tramo: str | None = None,
    entero: int | None = None,
    anulada: bool = False,
) -> LicenciaMedica:
    ing = _ingreso(db, sufijo)
    inicio = datetime.date(2026, 9, 1)
    lm = LicenciaMedica(
        ingreso_id=ing.id,
        tipo_lm="5",
        tipo_reposo="total",
        fecha_inicio=inicio,
        fecha_termino=inicio + datetime.timedelta(days=60),
        fecha_emision=inicio,
        inicio_reposo=inicio,
        fin_reposo=inicio + datetime.timedelta(days=60),
        cantidad_dias=61,
        diagnostico="F32.1",
        origen="sistema",
        envio_isl="pendiente",
        eeag_gaf=entero,
        eeag_gaf_tramo=tramo,
        anulada=anulada,
    )
    db.add(lm)
    db.flush()
    return lm


def _alertas_gaf(db: Session, lm: LicenciaMedica) -> int:
    return db.scalar(
        select(func.count()).select_from(AlertaNotif).where(
            AlertaNotif.caso_id == lm.id, AlertaNotif.tipo == "gaf_licencia"
        )
    )


def _configurar_gaf(db: Session, umbral: int, activo: bool = True) -> None:
    fila = db.scalars(select(ConfigAlerta).where(ConfigAlerta.tipo == "gaf_licencia")).one()
    fila.dias, fila.activo = umbral, activo
    db.flush()


# ── Helper de dominio ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [(1, "1-10"), (10, "1-10"), (11, "11-20"), (45, "41-50"), (100, "91-100")],
)
def test_tramo_que_contiene(valor, esperado):
    assert tramo_que_contiene(valor, TRAMOS_EEAG).etiqueta == esperado


@pytest.mark.parametrize("valor", [None, 0, 101, -5])
def test_tramo_que_contiene_fuera_de_catalogo(valor):
    assert tramo_que_contiene(valor, TRAMOS_EEAG) is None


def test_tramo_que_contiene_con_catalogo_propio():
    propio = [Tramo(1, 30, "1-30"), Tramo(31, 100, "31-100")]
    assert tramo_que_contiene(30, propio).etiqueta == "1-30"
    assert tramo_que_contiene(31, propio).etiqueta == "31-100"


# ── Migración ───────────────────────────────────────────────────────────────


def test_migracion_siembra_diez_tramos_provisorios(db_session: Session):
    tramos = list(db_session.scalars(select(GafTramo).order_by(GafTramo.orden)))
    assert [t.etiqueta for t in tramos] == [f"{d}-{d + 9}" for d in range(1, 92, 10)]
    assert tramos[-1].etiqueta == "91-100"
    assert all(t.activo and t.provisorio for t in tramos)
    assert all(t.desde < t.hasta for t in tramos)


def test_migracion_siembra_alerta_gaf_desactivada(db_session: Session):
    fila = db_session.scalars(
        select(ConfigAlerta).where(ConfigAlerta.tipo == "gaf_licencia")
    ).one()
    assert fila.activo is False


def _migracion_1300():
    ruta = Path(__file__).parent.parent / "migrations" / "versions" / "1300_gaf_tramo.py"
    spec = importlib.util.spec_from_file_location("migracion_1300", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_relleno_de_tramos_desde_enteros(db_session: Session):
    """El UPDATE de la migración asigna el tramo que contiene al entero ya cargado."""
    lm = _licencia(db_session, "0001", entero=45)
    lm_cero = _licencia(db_session, "0002", entero=0)
    lm_con_tramo = _licencia(db_session, "0003", entero=45, tramo="61-70")
    ing = _ingreso(db_session, "0004")
    ctrl = ControlMedico(
        ingreso_id=ing.id,
        fecha_control=datetime.date(2026, 2, 2),
        semana_control=5,
        medico_tratante="Dr. Test",
        region_derivacion="Maule",
        gaf=72,
    )
    db_session.add(ctrl)
    db_session.flush()

    for sentencia in _migracion_1300().SQL_RELLENO:
        db_session.execute(text(sentencia))
    for obj in (lm, lm_cero, lm_con_tramo, ctrl):
        db_session.refresh(obj)

    assert lm.eeag_gaf_tramo == "41-50"
    assert lm_cero.eeag_gaf_tramo is None  # 0 no cae en ningún tramo: queda el entero
    assert lm_con_tramo.eeag_gaf_tramo == "61-70"  # no pisa un tramo ya cargado
    assert ctrl.gaf_tramo == "71-80"


# ── Endpoint del catálogo ───────────────────────────────────────────────────


def test_get_gaf_tramos_para_los_tres_roles(
    as_admin: TestClient, as_coordinacion: TestClient, as_auditor: TestClient
):
    for cliente in (as_admin, as_coordinacion, as_auditor):
        resp = cliente.get("/api/v1/gaf-tramos")
        assert resp.status_code == 200, resp.text
        cuerpo = resp.json()
        assert len(cuerpo) == 10
        assert cuerpo[0] == {
            "id": cuerpo[0]["id"],
            "desde": 1,
            "hasta": 10,
            "etiqueta": "1-10",
            "orden": 1,
            "provisorio": True,
        }


def test_get_gaf_tramos_sin_sesion(client: TestClient):
    assert client.get("/api/v1/gaf-tramos").status_code == 401


def test_get_gaf_tramos_excluye_inactivos(as_admin: TestClient, db_session: Session):
    tramo = db_session.scalars(select(GafTramo).where(GafTramo.etiqueta == "1-10")).one()
    tramo.activo = False
    db_session.flush()
    etiquetas = [t["etiqueta"] for t in as_admin.get("/api/v1/gaf-tramos").json()]
    assert "1-10" not in etiquetas and len(etiquetas) == 9


# ── Formularios: control médico y licencia (ISL) ────────────────────────────


def _crear_control(as_admin: TestClient, db: Session, sufijo: str) -> dict:
    ing = _ingreso(db, sufijo)
    resp = as_admin.post(
        "/api/v1/controles-medicos",
        json={
            "ingreso_id": ing.id,
            "fecha_control": "2026-02-02",
            "medico_tratante": "Dr. Ramírez",
            "region_derivacion": "Maule",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _licencia_control(**extra) -> dict:
    return {
        "tiene_licencia": True,
        "resumen_termino_lm": "LM 15 días",
        "total_dias_lm": 15,
        "tipo_licencia": "1",
        "tipo_reposo": "total",
        **extra,
    }


def test_control_guarda_tramo_de_gaf(as_admin: TestClient, db_session: Session):
    ctrl = _crear_control(as_admin, db_session, "0101")
    resp = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/licencia",
        json=_licencia_control(gaf_tramo="41-50"),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["gaf_tramo"] == "41-50"


def test_control_rechaza_tramo_fuera_de_catalogo(as_admin: TestClient, db_session: Session):
    ctrl = _crear_control(as_admin, db_session, "0102")
    resp = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/licencia",
        json=_licencia_control(gaf_tramo="45-55"),
    )
    assert resp.status_code == 422, resp.text


def test_control_con_entero_deriva_el_tramo(as_admin: TestClient, db_session: Session):
    ctrl = _crear_control(as_admin, db_session, "0103")
    resp = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/licencia", json=_licencia_control(gaf=55)
    )
    assert resp.status_code == 200, resp.text
    assert (resp.json()["gaf"], resp.json()["gaf_tramo"]) == (55, "51-60")


def test_control_elegir_tramo_conserva_el_entero(as_admin: TestClient, db_session: Session):
    ctrl = _crear_control(as_admin, db_session, "0104")
    as_admin.patch(f"/api/v1/controles-medicos/{ctrl['id']}/licencia", json=_licencia_control(gaf=55))
    resp = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/licencia",
        json=_licencia_control(gaf_tramo="61-70"),
    )
    assert (resp.json()["gaf"], resp.json()["gaf_tramo"]) == (55, "61-70")


def test_licencia_isl_guarda_tramo(as_admin: TestClient, db_session: Session):
    lm = _licencia(db_session, "0201")
    resp = as_admin.patch(
        f"/api/v1/licencias/{lm.id}/isl",
        json={"envio_isl": "pendiente", "eeag_gaf_tramo": "21-30"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["eeag_gaf_tramo"] == "21-30"

    hist = as_admin.get(f"/api/v1/ingresos/{lm.ingreso_id}/licencias").json()
    assert next(x for x in hist if x["id"] == lm.id)["eeag_gaf_tramo"] == "21-30"


def test_licencia_isl_rechaza_tramo_fuera_de_catalogo(as_admin: TestClient, db_session: Session):
    lm = _licencia(db_session, "0202")
    resp = as_admin.patch(
        f"/api/v1/licencias/{lm.id}/isl",
        json={"envio_isl": "pendiente", "eeag_gaf_tramo": "0-5"},
    )
    assert resp.status_code == 422, resp.text


def test_licencia_isl_con_entero_deriva_el_tramo(as_admin: TestClient, db_session: Session):
    lm = _licencia(db_session, "0203")
    resp = as_admin.patch(
        f"/api/v1/licencias/{lm.id}/isl", json={"envio_isl": "pendiente", "eeag_gaf": 33}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["eeag_gaf_tramo"] == "31-40"


# ── COMP-2609-20: alerta por tramo de GAF en licencia ───────────────────────


def test_alerta_gaf_desactivada_no_genera(db_session: Session):
    lm = _licencia(db_session, "0301", tramo="1-10")
    ejecutar_job_alertas(db_session, hoy=HOY)
    assert _alertas_gaf(db_session, lm) == 0  # RN-2 / TC-075-03


def test_alerta_gaf_en_o_bajo_umbral(db_session: Session):
    _configurar_gaf(db_session, umbral=50)
    bajo = _licencia(db_session, "0302", tramo="1-10")  # TC-075-01
    limite = _licencia(db_session, "0303", tramo="41-50")
    sobre = _licencia(db_session, "0304", tramo="81-90")  # TC-075-02
    solo_entero = _licencia(db_session, "0305", entero=35)
    anulada = _licencia(db_session, "0306", tramo="1-10", anulada=True)
    sin_gaf = _licencia(db_session, "0307")

    ejecutar_job_alertas(db_session, hoy=HOY)

    assert _alertas_gaf(db_session, bajo) == 1
    assert _alertas_gaf(db_session, limite) == 1
    assert _alertas_gaf(db_session, sobre) == 0
    assert _alertas_gaf(db_session, solo_entero) == 1
    assert _alertas_gaf(db_session, anulada) == 0
    assert _alertas_gaf(db_session, sin_gaf) == 0

    alerta = db_session.scalars(
        select(AlertaNotif).where(AlertaNotif.caso_id == bajo.id, AlertaNotif.tipo == "gaf_licencia")
    ).one()
    assert alerta.caso_tipo == "licencia"
    assert alerta.ventana_dias == 50  # umbral vigente al generar


def test_alerta_gaf_idempotente(db_session: Session):
    _configurar_gaf(db_session, umbral=30)
    lm = _licencia(db_session, "0401", tramo="21-30")
    ejecutar_job_alertas(db_session, hoy=HOY)
    ejecutar_job_alertas(db_session, hoy=HOY + datetime.timedelta(days=1))
    assert _alertas_gaf(db_session, lm) == 1  # CA-4 / TC-075-05


def test_alerta_gaf_cambio_de_umbral_sin_redespliegue(as_coordinacion: TestClient, db_session: Session):
    lm = _licencia(db_session, "0501", tramo="51-60")
    resp = as_coordinacion.put(
        "/api/v1/config-alertas",
        json=[{"tipo": "gaf_licencia", "dias": 40, "habiles": False, "activo": True}],
    )
    assert resp.status_code == 200, resp.text
    ejecutar_job_alertas(db_session, hoy=HOY)
    assert _alertas_gaf(db_session, lm) == 0

    as_coordinacion.put(
        "/api/v1/config-alertas",
        json=[{"tipo": "gaf_licencia", "dias": 60, "habiles": False, "activo": True}],
    )
    ejecutar_job_alertas(db_session, hoy=HOY)
    assert _alertas_gaf(db_session, lm) == 1  # CA-3 / TC-075-04


def test_umbral_gaf_mayor_a_100_rechazado(as_coordinacion: TestClient):
    resp = as_coordinacion.put(
        "/api/v1/config-alertas",
        json=[{"tipo": "gaf_licencia", "dias": 150, "habiles": False, "activo": True}],
    )
    assert resp.status_code == 422
