"""QA-003: casos activos por paciente y listado de pacientes con casos repetidos."""

import datetime

from sqlalchemy.dialects import oracle

from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.reintegro import CasoReintegro
from app.services.reintegro import (
    consulta_pacientes_con_casos_activos_repetidos,
    listar_pacientes_con_casos_repetidos,
)


def _paciente(db, rut: str, nombre: str) -> Paciente:
    p = Paciente(rut=rut, nombre=nombre, sexo="M", edad=40, region="Maule")
    db.add(p)
    db.flush()
    return p


def _ingreso(db, paciente: Paciente, folio: str, razon_social: str | None = None) -> Ingreso:
    ing = Ingreso(
        paciente_id=paciente.id,
        folio=folio,
        folio_manual=True,
        fecha_ingreso=datetime.date(2026, 1, 10),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="Trastorno adaptativo",
        estado="activo",
        razon_social=razon_social,
    )
    db.add(ing)
    db.flush()
    return ing


def _caso(db, ingreso: Ingreso, paciente: Paciente, estado="pendiente", fecha=None, **kw):
    caso = CasoReintegro(
        ingreso_id=ingreso.id,
        rut=paciente.rut,
        nombre=paciente.nombre,
        tipo_derivacion="DIAT",
        fecha_caso=fecha or datetime.date(2026, 3, 1),
        region=kw.pop("region", "Maule"),
        razon_social=kw.pop("razon_social", None),
        estado_reintegro=estado,
    )
    db.add(caso)
    db.flush()
    return caso


def test_listado_solo_pacientes_con_mas_de_un_caso_activo(db_session):
    db = db_session
    dup = _paciente(db, "111111111", "Duplicada Uno")
    ing1 = _ingreso(db, dup, "F-DUP-1")
    ing2 = _ingreso(db, dup, "F-DUP-2")
    c1 = _caso(db, ing1, dup, region="Maule", razon_social="Empresa A")
    c2 = _caso(db, ing2, dup, estado="parcial", region="Biobío", razon_social="Empresa B")

    unico = _paciente(db, "222222222", "Un Solo Caso")
    _caso(db, _ingreso(db, unico, "F-UNI-1"), unico)

    cerrado = _paciente(db, "333333333", "Uno Activo Uno Cerrado")
    ingc = _ingreso(db, cerrado, "F-CER-1")
    _caso(db, ingc, cerrado)
    _caso(db, ingc, cerrado, estado="total")

    resultado = listar_pacientes_con_casos_repetidos(db)

    ids = [r.paciente_id for r in resultado]
    assert ids == [dup.id]
    fila = resultado[0]
    assert fila.nombre == "Duplicada Uno"
    assert fila.rut == "111111111"
    assert [c.id for c in fila.casos] == [c1.id, c2.id]
    assert fila.casos[0].region == "Maule"
    assert fila.casos[0].razon_social == "Empresa A"
    assert fila.casos[1].estado_reintegro == "parcial"
    assert fila.casos[1].ingreso_id == ing2.id


def test_dos_casos_del_mismo_ingreso_cuentan_como_duplicado(db_session):
    db = db_session
    p = _paciente(db, "444444444", "Mismo Ingreso")
    ing = _ingreso(db, p, "F-MI-1")
    _caso(db, ing, p)
    _caso(db, ing, p)
    assert [r.paciente_id for r in listar_pacientes_con_casos_repetidos(db)] == [p.id]


def test_casos_cerrados_no_cuentan_como_activos(db_session):
    db = db_session
    p = _paciente(db, "555555555", "Todos Cerrados")
    ing = _ingreso(db, p, "F-TC-1")
    _caso(db, ing, p, estado="total")
    _caso(db, ing, p, estado="total")
    assert listar_pacientes_con_casos_repetidos(db) == []


def test_endpoint_duplicados_lo_leen_los_roles_de_lectura(as_auditor, db_session):
    db = db_session
    p = _paciente(db, "666666666", "Endpoint Dup")
    ing = _ingreso(db, p, "F-ED-1")
    c1 = _caso(db, ing, p)
    c2 = _caso(db, ing, p)
    db.commit()

    r = as_auditor.get("/api/v1/reintegros/duplicados")
    assert r.status_code == 200, r.text
    filas = [f for f in r.json() if f["paciente_id"] == p.id]
    assert len(filas) == 1
    assert filas[0]["rut"] == "666666666"
    assert [c["id"] for c in filas[0]["casos"]] == [c1.id, c2.id]
    assert set(filas[0]["casos"][0]) >= {
        "id", "ingreso_id", "region", "razon_social", "fecha_caso", "estado_reintegro",
    }


def test_endpoint_duplicados_es_de_solo_lectura_y_exige_sesion(client):
    assert client.get("/api/v1/reintegros/duplicados").status_code in (401, 403)


def test_listado_filtra_casos_activos_de_un_paciente(as_admin, db_session):
    db = db_session
    p = _paciente(db, "777777777", "Filtro Paciente")
    ing1 = _ingreso(db, p, "F-FP-1")
    ing2 = _ingreso(db, p, "F-FP-2")
    activo1 = _caso(db, ing1, p)
    activo2 = _caso(db, ing2, p, estado="parcial")
    _caso(db, ing2, p, estado="total")
    otro = _paciente(db, "888888888", "Otro")
    _caso(db, _ingreso(db, otro, "F-FP-3"), otro)
    db.commit()

    r = as_admin.get(f"/api/v1/reintegros?paciente_id={p.id}&solo_activos=true")
    assert r.status_code == 200, r.text
    assert [c["id"] for c in r.json()] == [activo1.id, activo2.id]

    todos = as_admin.get(f"/api/v1/reintegros?paciente_id={p.id}")
    assert len(todos.json()) == 3


def test_consulta_compila_en_oracle():
    sql = str(
        consulta_pacientes_con_casos_activos_repetidos().compile(dialect=oracle.dialect())
    )
    assert "HAVING" in sql.upper()
