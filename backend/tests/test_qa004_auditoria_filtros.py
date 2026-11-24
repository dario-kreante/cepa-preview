"""QA-004 (23-11-2026): filtros del reporte de auditoría sin mayúsculas ni tildes, con
programa del ingreso y convenio."""

import datetime

from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.schemas.auditoria import FiltrosReporte
from app.services.auditoria import generar_reporte


def _ingreso(db, folio, region, **extra):
    p = Paciente(rut=None, nombre=f"Paciente {folio}", sexo="F", edad=30, region=region)
    db.add(p)
    db.flush()
    datos = dict(
        paciente_id=p.id, folio=folio, folio_manual=True, fecha_ingreso=datetime.date(2026, 7, 1),
        tipo_derivacion="DIEP", tipo_ingreso="convenio", modelo_tratamiento="ambulatorio",
        diagnostico="Trastorno adaptativo", estado="activo",
    )
    datos.update(extra)
    db.add(Ingreso(**datos))
    db.flush()


def _folios(db, **filtros):
    f = FiltrosReporte(fecha_desde=datetime.date(2026, 7, 1), fecha_hasta=datetime.date(2026, 7, 31), **filtros)
    return sorted(x.folio for x in generar_reporte(db, f).filas)


def test_region_y_estado_sin_mayusculas_ni_tildes(db_session):
    _ingreso(db_session, "QA4-1", "Biobío")
    _ingreso(db_session, "QA4-2", "Maule")

    assert _folios(db_session, region="biobio") == ["QA4-1"]
    assert _folios(db_session, region="BIOBÍO") == ["QA4-1"]
    assert _folios(db_session, estado_caso="Activo") == ["QA4-1", "QA4-2"]


def test_programa_del_ingreso_y_convenio(db_session):
    _ingreso(db_session, "QA4-3", "Maule", programa="Ingreso ISL", tipo_convenio="Convenio ISL MAULE")
    _ingreso(db_session, "QA4-4", "Maule", programa="PIPT")

    assert _folios(db_session, programa="Ingreso ISL") == ["QA4-3"]
    assert _folios(db_session, convenio="Convenio ISL MAULE") == ["QA4-3"]
    [fila] = [x for x in generar_reporte(db_session, FiltrosReporte(
        fecha_desde=datetime.date(2026, 7, 1), fecha_hasta=datetime.date(2026, 7, 31), programa="Ingreso ISL",
    )).filas]
    assert (fila.programa, fila.convenio, fila.tipo_ingreso) == ("Ingreso ISL", "Convenio ISL MAULE", "convenio")
