from datetime import datetime, timedelta, timezone

from app.models.salutem_sync import SalutemSyncEjecucion

URL = "/api/v1/salutem/sync/estado"


def _ejecucion(db, modo, estado, hace_min):
    fin = datetime.now(timezone.utc) - timedelta(minutes=hace_min)
    db.add(
        SalutemSyncEjecucion(
            modo=modo, estado=estado, inicio=fin - timedelta(minutes=1), fin=fin,
            llamadas=10, nuevos=1, cambiados=0, desaparecidos=0,
        )
    )
    db.flush()


def test_sin_ejecuciones_esta_atrasado(as_coordinacion):
    r = as_coordinacion.get(URL)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["atrasado"] is True
    assert cuerpo["ultimas"] == {}
    assert cuerpo["atenciones"] == 0


def test_una_caliente_reciente_lo_deja_al_dia(as_coordinacion, db_session):
    _ejecucion(db_session, "caliente", "ok", hace_min=3)
    cuerpo = as_coordinacion.get(URL).json()
    assert cuerpo["atrasado"] is False
    assert cuerpo["ultimas"]["caliente"]["llamadas"] == 10


def test_una_caliente_vieja_esta_atrasada_y_las_omitidas_no_cuentan(as_coordinacion, db_session):
    _ejecucion(db_session, "caliente", "ok", hace_min=45)
    _ejecucion(db_session, "caliente", "omitida", hace_min=1)
    cuerpo = as_coordinacion.get(URL).json()
    assert cuerpo["atrasado"] is True
    assert cuerpo["ultimas"]["caliente"]["estado"] == "ok"


def test_otros_roles_no_acceden(as_auditor):
    assert as_auditor.get(URL).status_code == 403
