"""Sincronización del catálogo de convenios de SALUTEM (sin llamadas a la API)."""

import pytest
from sqlalchemy import func, select

from app.integrations.salutem.errors import SalutemUnavailableError
from app.models.audit_log import AuditLog
from app.models.convenio import Convenio
from app.services.convenios_sync import sincronizar_convenios
from tests.salutem_falso import SalutemFalso
from tests.salutem_sync.conftest import AHORA


def _falso(*filas: tuple[int, str, bool]) -> SalutemFalso:
    s = SalutemFalso()
    s.convenios = [{"id": i, "nombre": n, "activo": a, "tipo": "CONVENIO"} for i, n, a in filas]
    return s


def _convenio(db, nombre, salutem_id=None, visible=True, activo=True):
    from app.services.salutem_sync.profesionales import normalizar_nombre

    c = Convenio(
        nombre=nombre, nombre_normalizado=normalizar_nombre(nombre), salutem_id=salutem_id,
        visible=visible, activo_salutem=activo,
    )
    db.add(c)
    db.flush()
    return c


def _por_sid(db, sid):
    return db.scalars(select(Convenio).where(Convenio.salutem_id == sid)).one()


def test_crea_convenios_y_sin_convenio_nace_oculto(db_session):
    r = sincronizar_convenios(db_session, _falso((1486, "Colegio Inglés", True), (1415, "Sin Convenio", True)), AHORA)

    assert r.creados == 2
    assert _por_sid(db_session, 1486).visible is True
    assert _por_sid(db_session, 1415).visible is False


def test_adopta_manual_por_nombre_sin_tildes_ni_mayusculas(db_session):
    manual = _convenio(db_session, "convenio colegio ingles")

    r = sincronizar_convenios(db_session, _falso((1486, "Convenio Colegio Inglés", True)), AHORA)

    assert r.creados == 0
    assert manual.salutem_id == 1486
    assert db_session.scalar(select(func.count()).select_from(Convenio)) == 1


def test_no_toca_visible_de_uno_existente(db_session):
    _convenio(db_session, "Colegio Inglés", salutem_id=1486, visible=False)

    sincronizar_convenios(db_session, _falso((1486, "Colegio Inglés", True)), AHORA)

    assert _por_sid(db_session, 1486).visible is False


def test_desactiva_el_que_ya_no_viene(db_session):
    _convenio(db_session, "Antiguo", salutem_id=1237)
    manual = _convenio(db_session, "Manual")

    r = sincronizar_convenios(db_session, _falso((1486, "Nuevo", True)), AHORA)

    assert r.desactivados == 1
    assert _por_sid(db_session, 1237).activo_salutem is False
    assert manual.activo_salutem is True and manual.salutem_id is None


def test_renombre_arrastra_ingresos_y_audita_una_vez(db_session, ingreso_fixture):
    conv = _convenio(db_session, "Convenio ISL MAULE", salutem_id=1345)
    ingreso_fixture.tipo_convenio = "Convenio ISL MAULE"
    db_session.flush()

    r = sincronizar_convenios(db_session, _falso((1345, "Convenio ISL Maule", True)), AHORA)

    db_session.refresh(ingreso_fixture)
    assert ingreso_fixture.tipo_convenio == "Convenio ISL Maule"
    assert conv.nombre == "Convenio ISL Maule"
    assert r.renombrados == 1 and r.ingresos_renombrados == 1
    trazas = db_session.scalars(select(AuditLog).where(AuditLog.action == "convenio_renombrado")).all()
    assert len(trazas) == 1
    assert trazas[0].valor_anterior == "Convenio ISL MAULE"
    assert trazas[0].valor_nuevo == "Convenio ISL Maule (1 ingresos)"


def test_renombre_que_choca_se_salta_y_se_informa(db_session):
    ranger = _convenio(db_session, "Convenio Ranger", salutem_id=1500)
    manual = _convenio(db_session, "Convenio Rangers")

    r = sincronizar_convenios(db_session, _falso((1500, "Convenio RANGERS", True)), AHORA)

    assert ranger.nombre == "Convenio Ranger"
    assert manual.nombre == "Convenio Rangers" and manual.salutem_id is None
    assert len(r.errores) == 1 and "ya existe" in r.errores[0]
    assert r.renombrados == 0


def test_segunda_pasada_no_cambia_nada(db_session):
    salutem = _falso((1486, "Colegio Inglés", True), (1415, "Sin Convenio", True), (7, "Viejo", False))
    sincronizar_convenios(db_session, salutem, AHORA)

    r = sincronizar_convenios(db_session, salutem, AHORA)

    assert r.creados == r.actualizados == r.desactivados == r.renombrados == 0
    assert r.errores == []


class _Caido(SalutemFalso):
    def listar_convenios(self):
        raise SalutemUnavailableError("caído")


def test_salutem_caido_propaga_y_no_cambia_nada(db_session):
    _convenio(db_session, "Existente", salutem_id=1)

    with pytest.raises(SalutemUnavailableError):
        sincronizar_convenios(db_session, _Caido(), AHORA)

    assert db_session.scalar(select(func.count()).select_from(Convenio)) == 1
    assert _por_sid(db_session, 1).activo_salutem is True
