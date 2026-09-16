from datetime import timedelta
from zoneinfo import ZoneInfo

import pytest

from app.models.salutem_sync import SalutemSyncEjecucion, SalutemSyncLease
from app.services.salutem_sync.bitacora import abrir_ejecucion, cerrar_ejecucion, registrar_omitida
from app.services.salutem_sync.lease import soltar_lease, tomar_lease
from app.services.salutem_sync.tipos import Contadores
from tests.salutem_sync.conftest import AHORA


def test_toma_el_lease_libre(db_session):
    assert tomar_lease(db_session, "proceso-a", AHORA)


def test_otro_proceso_no_puede_tomar_un_lease_vigente(db_session):
    assert tomar_lease(db_session, "proceso-a", AHORA)
    assert not tomar_lease(db_session, "proceso-b", AHORA + timedelta(minutes=1))


def test_el_mismo_dueno_lo_renueva(db_session):
    assert tomar_lease(db_session, "proceso-a", AHORA)
    assert tomar_lease(db_session, "proceso-a", AHORA + timedelta(minutes=5))


def test_un_lease_vencido_se_recupera(db_session):
    assert tomar_lease(db_session, "proceso-a", AHORA)
    assert tomar_lease(db_session, "proceso-b", AHORA + timedelta(minutes=31))


def test_tomar_lease_normaliza_horario_no_utc(db_session):
    """Un `ahora` con tzinfo distinto de UTC (p.ej. hora local de Santiago) se comporta
    igual que el mismo instante en UTC: otro dueño no puede tomarlo 1 minuto después."""
    ahora_santiago = AHORA.astimezone(ZoneInfo("America/Santiago"))
    assert tomar_lease(db_session, "proceso-a", ahora_santiago)
    assert not tomar_lease(db_session, "proceso-b", AHORA + timedelta(minutes=1))


def test_tomar_lease_rechaza_horario_naive(db_session):
    with pytest.raises(ValueError):
        tomar_lease(db_session, "proceso-a", AHORA.replace(tzinfo=None))


def test_soltar_lo_libera(db_session):
    assert tomar_lease(db_session, "proceso-a", AHORA)
    soltar_lease(db_session, "proceso-a")
    assert db_session.get(SalutemSyncLease, "salutem").dueno is None
    assert tomar_lease(db_session, "proceso-b", AHORA)


def test_bitacora_abre_y_cierra_con_contadores(db_session):
    ejecucion = abrir_ejecucion(db_session, "caliente", AHORA)
    assert ejecucion.estado == "en_curso"

    cerrar_ejecucion(
        db_session,
        ejecucion,
        estado="ok",
        ahora=AHORA + timedelta(minutes=1),
        llamadas=36,
        contadores=Contadores(nuevos=2, cambiados=1, desaparecidos=0),
    )

    guardada = db_session.get(SalutemSyncEjecucion, ejecucion.id)
    assert (guardada.estado, guardada.llamadas, guardada.nuevos, guardada.cambiados) == ("ok", 36, 2, 1)
    assert guardada.fin is not None


def test_bitacora_recorta_errores_largos(db_session):
    ejecucion = abrir_ejecucion(db_session, "tibia", AHORA)
    cerrar_ejecucion(db_session, ejecucion, estado="error", ahora=AHORA, error="x" * 5000)
    assert len(db_session.get(SalutemSyncEjecucion, ejecucion.id).error) == 2000


def test_registra_una_ejecucion_omitida(db_session):
    omitida = registrar_omitida(db_session, "caliente", AHORA)
    assert db_session.get(SalutemSyncEjecucion, omitida.id).estado == "omitida"
