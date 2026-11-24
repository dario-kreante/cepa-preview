"""QA-007: historial de cierres y reaperturas del caso (tabla ingreso_cierre, migración 1520)."""

from datetime import datetime, timezone

from sqlalchemy import delete, inspect, select
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models.ingreso import Ingreso
from app.models.ingreso_cierre import HistorialCierre
from app.models.paciente import Paciente


def _ingreso(as_admin, **over):
    base = {
        "rut": "11.111.111-1",
        "nombre": "Ana González",
        "sexo": "F",
        "edad": 33,
        "region": "Maule",
        "diagnostico": "x",
        "tipo_derivacion": "DIAT",
        "tipo_ingreso": "convenio",
        "modelo_tratamiento": "ambulatorio",
        "fecha_ingreso": "2026-06-01",
    }
    base.update(over)
    return as_admin.post("/api/v1/ingresos", json=base).json()


def _patch(cli, ing_id, **body):
    return cli.patch(f"/api/v1/ingresos/{ing_id}/estado", json=body)


def _cierres(cli, ing_id):
    return cli.get(f"/api/v1/ingresos/{ing_id}/cierres")


def test_sin_cierres_el_historial_esta_vacio(as_admin):
    ing = _ingreso(as_admin)
    r = _cierres(as_admin, ing["id"])
    assert r.status_code == 200
    assert r.json() == []


def test_historial_de_ingreso_inexistente_es_404(as_admin):
    assert _cierres(as_admin, 999_999_999).status_code == 404


def test_cerrar_deja_una_fila_en_el_historial(as_admin):
    ing = _ingreso(as_admin)
    _patch(as_admin, ing["id"], estado="cerrado", motivo_cierre="alta_medica")
    filas = _cierres(as_admin, ing["id"]).json()
    assert len(filas) == 1
    f = filas[0]
    assert f["motivo_cierre"] == "alta_medica"
    assert f["cerrado_por"] == "admin_test"
    assert f["fecha_cierre"] is not None and f["cerrado_en"] is not None
    assert f["reabierto_por"] is None and f["reabierto_en"] is None and f["motivo_reapertura"] is None


def test_post_cierre_tambien_registra_historial(as_admin):
    ing = _ingreso(as_admin)
    as_admin.post(
        f"/api/v1/ingresos/{ing['id']}/cierre",
        json={"estado": "cerrado", "motivo_cierre": "reca_ec"},
    )
    filas = _cierres(as_admin, ing["id"]).json()
    assert [f["motivo_cierre"] for f in filas] == ["reca_ec"]


def test_derivar_no_registra_cierre(as_admin):
    ing = _ingreso(as_admin)
    as_admin.post(f"/api/v1/ingresos/{ing['id']}/cierre", json={"estado": "derivado"})
    assert _cierres(as_admin, ing["id"]).json() == []


def test_cierre_reapertura_y_nuevo_cierre_dejan_dos_filas(as_admin, as_coordinacion):
    ing = _ingreso(as_admin)
    _patch(as_admin, ing["id"], estado="cerrado", motivo_cierre="abandono")
    r = _patch(
        as_coordinacion, ing["id"], estado="activo", motivo_reapertura="  Retoma el tratamiento  "
    )
    assert r.status_code == 200
    # El ingreso ya no muestra el cierre anterior…
    assert r.json()["motivo_cierre"] is None
    # …pero el historial lo conserva.
    _patch(as_admin, ing["id"], estado="cerrado", motivo_cierre="alta_medica")

    filas = _cierres(as_coordinacion, ing["id"]).json()
    assert len(filas) == 2
    reciente, anterior = filas
    assert reciente["motivo_cierre"] == "alta_medica"
    assert reciente["reabierto_en"] is None
    assert anterior["motivo_cierre"] == "abandono"
    assert anterior["cerrado_por"] == "admin_test"
    assert anterior["reabierto_por"] == "coord_test"
    assert anterior["reabierto_en"] is not None
    assert anterior["motivo_reapertura"] == "Retoma el tratamiento"


def test_reapertura_sin_motivo_lo_deja_vacio(as_admin, as_coordinacion):
    ing = _ingreso(as_admin)
    _patch(as_admin, ing["id"], estado="cerrado", motivo_cierre="abandono")
    _patch(as_coordinacion, ing["id"], estado="activo", motivo_reapertura="   ")
    (fila,) = _cierres(as_admin, ing["id"]).json()
    assert fila["reabierto_por"] == "coord_test"
    assert fila["motivo_reapertura"] is None


def test_motivo_de_reapertura_fuera_de_reapertura_es_422(as_admin):
    ing = _ingreso(as_admin)
    r = _patch(as_admin, ing["id"], estado="encuadre", motivo_reapertura="x")
    assert r.status_code == 422
    r = _patch(as_admin, ing["id"], estado="cerrado", motivo_cierre="abandono", motivo_reapertura="x")
    assert r.status_code == 422
    assert _cierres(as_admin, ing["id"]).json() == []


def test_motivo_de_reapertura_largo_es_422(as_admin, as_coordinacion):
    ing = _ingreso(as_admin)
    _patch(as_admin, ing["id"], estado="cerrado", motivo_cierre="abandono")
    r = _patch(as_coordinacion, ing["id"], estado="activo", motivo_reapertura="x" * 301)
    assert r.status_code == 422


def test_reapertura_rechazada_no_toca_el_historial(as_admin):
    ing = _ingreso(as_admin)
    _patch(as_admin, ing["id"], estado="cerrado", motivo_cierre="abandono")
    assert _patch(as_admin, ing["id"], estado="activo").status_code == 403
    (fila,) = _cierres(as_admin, ing["id"]).json()
    assert fila["reabierto_en"] is None


def test_auditor_lee_el_historial(as_admin, as_auditor):
    ing = _ingreso(as_admin)
    _patch(as_admin, ing["id"], estado="cerrado", motivo_cierre="abandono")
    assert len(_cierres(as_auditor, ing["id"]).json()) == 1


# ── Migración 1520 ────────────────────────────────────────────────────────────
def test_tabla_ingreso_cierre_existe():
    cols = {c["name"] for c in inspect(engine).get_columns("ingreso_cierre")}
    assert {
        "id", "ingreso_id", "motivo_cierre", "fecha_cierre", "cerrado_por", "cerrado_en",
        "reabierto_por", "reabierto_en", "motivo_reapertura",
    } <= cols


def test_la_migracion_siembra_los_cerrados_y_baja_limpia():
    from alembic import command  # noqa: PLC0415

    from tests.conftest import _alembic_config  # noqa: PLC0415

    cfg = _alembic_config()
    cuando = datetime(2026, 11, 20, 15, 0, tzinfo=timezone.utc)
    command.downgrade(cfg, "1510")
    paciente_id: int | None = None
    ids: list[int] = []
    try:
        assert not inspect(engine).has_table("ingreso_cierre")
        with Session(bind=engine) as s:
            paciente = Paciente(rut="99999999-9", nombre="Migración 1520")
            s.add(paciente)
            s.flush()
            paciente_id = paciente.id
            for folio, estado, motivo in (
                ("M1520-A", "cerrado", "alta_medica"),
                ("M1520-B", "cerrado", None),  # cerrado antes de QA-011: sin motivo, no se siembra
                ("M1520-C", "activo", None),
            ):
                ing = Ingreso(
                    paciente_id=paciente_id, folio=folio, fecha_ingreso=cuando.date(),
                    tipo_derivacion="DIAT", tipo_ingreso="convenio", estado=estado,
                    motivo_cierre=motivo, fecha_cierre=cuando if motivo else None,
                    cierre_usuario="coord_x" if motivo else None,
                )
                s.add(ing)
                s.flush()
                ids.append(ing.id)
            s.commit()
        command.upgrade(cfg, "head")
        with Session(bind=engine) as s:
            filas = list(s.scalars(select(HistorialCierre).where(HistorialCierre.ingreso_id.in_(ids))))
            assert len(filas) == 1
            (f,) = filas
            assert (f.ingreso_id, f.motivo_cierre, f.cerrado_por) == (ids[0], "alta_medica", "coord_x")
            # Oracle devuelve TIMESTAMP WITH TIME ZONE sin tzinfo (python-oracledb); Postgres, con UTC.
            assert f.cerrado_en.replace(tzinfo=None) == cuando.replace(tzinfo=None)
            assert f.reabierto_en is None
    finally:
        command.upgrade(cfg, "head")
        with Session(bind=engine) as s:
            if ids:
                s.execute(delete(HistorialCierre).where(HistorialCierre.ingreso_id.in_(ids)))
                s.execute(delete(Ingreso).where(Ingreso.id.in_(ids)))
            if paciente_id is not None:
                s.execute(delete(Paciente).where(Paciente.id == paciente_id))
            s.commit()
