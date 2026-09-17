"""El pull manual y las licencias sugeridas conviven con las fichas que crea el sync."""

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select

from app.integrations.salutem.models import AtencionSalutem, CitaSalutem, PersonaSalutem
from app.models.ficha_clinica import FichaClinica
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente

EXTENSION = "Extiendo licencia médica tipo 6 total desde el 09/05/2024 por 21 días"


@pytest.fixture
def ingreso(db_session) -> Ingreso:
    p = Paciente(rut="8881112220", nombre="Convivencia Sync", sexo="M", edad=30, region="Maule")
    db_session.add(p)
    db_session.flush()
    ing = Ingreso(
        paciente_id=p.id, folio="F-2026-CONV", folio_manual=True, fecha_ingreso=date(2024, 1, 1),
        tipo_derivacion="DIAT", tipo_ingreso="convenio", modelo_tratamiento="ambulatorio",
        diagnostico="convivencia", estado="activo",
    )
    db_session.add(ing)
    db_session.flush()
    return ing


class _SalutemUnaAtencion:
    def resolver_persona(self, rut):  # noqa: ARG002
        return PersonaSalutem(salutem_id=42, identificacion=rut)

    def listar_atenciones(self, salutem_id):  # noqa: ARG002
        return [CitaSalutem(persona_id=42, cita_id=777, fecha=date(2026, 1, 15))]

    def obtener_atencion(self, salutem_id, cita_id):  # noqa: ARG002
        return AtencionSalutem(
            cita=CitaSalutem(persona_id=42, cita_id=777, fecha=date(2026, 1, 15)),
            contenido={"citaId": 777},
        )


def test_el_pull_manual_guarda_salutem_cita_id(monkeypatch, as_admin, db_session, ingreso):
    monkeypatch.setattr("app.services.ficha_clinica.get_salutem_client", _SalutemUnaAtencion)

    r = as_admin.post("/api/v1/fichas-clinicas/pull-salutem", json={"folio": ingreso.folio})

    assert r.status_code == 200, r.text
    assert r.json()[0]["salutem_cita_id"] == 777


def test_el_pull_manual_no_duplica_una_ficha_creada_por_el_sync(monkeypatch, as_admin, db_session, ingreso):
    db_session.add(
        FichaClinica(
            ingreso_id=ingreso.id, folio=ingreso.folio, origen="SALUTEM",
            contenido={"sin": "citaId"}, salutem_cita_id=777,
        )
    )
    db_session.flush()
    monkeypatch.setattr("app.services.ficha_clinica.get_salutem_client", _SalutemUnaAtencion)

    r = as_admin.post("/api/v1/fichas-clinicas/pull-salutem", json={"folio": ingreso.folio})

    assert r.status_code == 200, r.text
    assert r.json() == []
    total = db_session.scalars(select(FichaClinica).where(FichaClinica.ingreso_id == ingreso.id)).all()
    assert len(total) == 1


def test_licencias_sugeridas_ignoran_fichas_eliminadas_en_salutem(as_admin, db_session, ingreso):
    db_session.add(
        FichaClinica(
            ingreso_id=ingreso.id, folio=ingreso.folio, origen="SALUTEM", salutem_cita_id=900,
            eliminada_en_origen=datetime.now(timezone.utc),
            contenido={
                "citaId": 900,
                "citaFecha": "2024-05-06",
                "indicaciones": [{"tipo": 1, "nombre": "Indicaciones", "registro": EXTENSION}],
            },
        )
    )
    db_session.flush()

    r = as_admin.get(f"/api/v1/fichas-clinicas/{ingreso.folio}/licencias-sugeridas")

    assert r.status_code == 200, r.text
    assert r.json() == []
