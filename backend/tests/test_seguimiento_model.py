from sqlalchemy import Boolean, Date, String

from app.models.plazo_programa import PlazoPrograma
from app.models.seguimiento import Seguimiento


def test_columnas_seguimiento():
    cols = set(Seguimiento.__table__.columns.keys())
    assert cols == {
        "id",
        "ingreso_id",
        "fecha_acogida",
        "programa",
        "eval_medica_estado",
        "eval_medica_medico",
        "eval_medica_fecha",
        "eval_psico_estado",
        "eval_psico_psicologo",
        "eval_psico_fecha",
        "obstaculizacion",
        "plazo_informe",
        "fecha_envio_informe",
        "reca_ep_ec",
        "created_at",
        "updated_at",
    }


def test_portabilidad_y_tipos_seguimiento():
    tabla = Seguimiento.__table__
    for nombre in [tabla.name, *tabla.columns.keys()]:
        assert nombre == nombre.lower()
        assert len(nombre) <= 30
    assert isinstance(tabla.columns["eval_medica_estado"].type, String)
    assert isinstance(tabla.columns["fecha_acogida"].type, Date)
    assert isinstance(tabla.columns["obstaculizacion"].type, Boolean)


def test_fk_ingreso_unica():
    cols = Seguimiento.__table__.columns
    assert cols["ingreso_id"].unique is True  # 1:1 con ingreso
    fks = list(cols["ingreso_id"].foreign_keys)
    assert fks[0].column.table.name == "ingreso"


def test_plazo_programa_columnas():
    assert set(PlazoPrograma.__table__.columns.keys()) == {"programa", "dias_plazo_informe"}
