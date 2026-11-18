"""Un folio puede repetirse entre ingresos del MISMO paciente (reingreso, CEPA-011 RN-3).

Antes, cualquier búsqueda de ingreso por folio con `scalar_one_or_none()` fallaba con
`MultipleResultsFound` (500) en cuanto el folio tenía dos ingresos.
"""

import datetime

import pytest

from app.models.ingreso import Ingreso
from app.models.paciente import Paciente

FOLIO = "F-2026-REPE"


@pytest.fixture
def dos_ingresos_mismo_folio(db_session):
    paciente = Paciente(rut="111111111", nombre="Rosa Reingreso", sexo="F", edad=40, region="Maule")
    db_session.add(paciente)
    db_session.flush()
    comunes = dict(
        paciente_id=paciente.id,
        folio=FOLIO,
        folio_manual=True,
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="Trastorno adaptativo",
    )
    viejo = Ingreso(
        fecha_ingreso=datetime.date(2026, 1, 10),
        fecha_alta=datetime.date(2026, 3, 10),
        estado="cerrado",
        **comunes,
    )
    nuevo = Ingreso(fecha_ingreso=datetime.date(2026, 6, 10), estado="activo", **comunes)
    db_session.add_all([viejo, nuevo])
    db_session.flush()
    return viejo, nuevo


def test_listar_fichas_con_folio_repetido(as_admin, dos_ingresos_mismo_folio):
    r = as_admin.get(f"/api/v1/fichas-clinicas/{FOLIO}")
    assert r.status_code == 200, r.text


def test_push_ficha_con_folio_repetido_va_al_ingreso_mas_reciente(
    as_admin, db_session, dos_ingresos_mismo_folio
):
    from app.models.ficha_clinica import FichaClinica

    _, nuevo = dos_ingresos_mismo_folio
    r = as_admin.post(
        "/api/v1/fichas-clinicas",
        json={"folio": FOLIO, "origen": "SAM", "contenido": {"nota": "x"}},
    )
    assert r.status_code == 201, r.text
    assert db_session.get(FichaClinica, r.json()["id"]).ingreso_id == nuevo.id


def test_licencias_con_folio_repetido(as_admin, dos_ingresos_mismo_folio):
    _, nuevo = dos_ingresos_mismo_folio
    r = as_admin.get(f"/api/v1/licencias/folio/{FOLIO}")
    assert r.status_code == 200, r.text
    assert r.json()["ingreso_id"] == nuevo.id


def test_licencias_sugeridas_con_folio_repetido(as_admin, dos_ingresos_mismo_folio):
    r = as_admin.get(f"/api/v1/fichas-clinicas/{FOLIO}/licencias-sugeridas")
    assert r.status_code == 200, r.text


def test_folio_existe_con_folio_repetido(db_session, dos_ingresos_mismo_folio):
    from app.services.folio import folio_existe

    assert folio_existe(db_session, FOLIO) is True


def test_imed_verificar_folio_con_folio_repetido(db_session, dos_ingresos_mismo_folio):
    from app.services.imed import _verificar_folio

    _verificar_folio(db_session, FOLIO)  # no debe lanzar MultipleResultsFound


def test_pull_salutem_asigna_cada_atencion_al_ingreso_de_su_ventana(
    as_admin, db_session, dos_ingresos_mismo_folio, monkeypatch
):
    """Cada atención va al ingreso cuya ventana la contiene; la que cae fuera de todas
    (entre el alta del primero y el inicio del segundo) se descarta."""
    from types import SimpleNamespace

    from app.models.ficha_clinica import FichaClinica

    viejo, nuevo = dos_ingresos_mismo_folio
    fechas = {
        1: datetime.date(2026, 2, 1),  # ventana del ingreso viejo
        2: datetime.date(2026, 4, 1),  # entre ingresos: no pertenece a ninguno
        3: datetime.date(2026, 7, 1),  # ventana del ingreso nuevo
    }

    class _Cliente:
        def resolver_persona(self, rut):
            return SimpleNamespace(salutem_id=99)

        def listar_atenciones(self, salutem_id):
            return [SimpleNamespace(cita_id=k, fecha=f) for k, f in fechas.items()]

        def obtener_atencion(self, salutem_id, cita_id):
            return SimpleNamespace(contenido={"citaId": cita_id})

    monkeypatch.setattr("app.services.ficha_clinica.get_salutem_client", lambda: _Cliente())
    r = as_admin.post("/api/v1/fichas-clinicas/pull-salutem", json={"folio": FOLIO})
    assert r.status_code == 200, r.text
    por_cita = {
        f.salutem_cita_id: f.ingreso_id
        for f in db_session.query(FichaClinica).filter(FichaClinica.folio == FOLIO)
    }
    assert por_cita == {1: viejo.id, 3: nuevo.id}
