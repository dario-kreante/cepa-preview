"""Atención médica de SALUTEM que no es control: la vista de su alerta y sus documentos."""

from datetime import date, datetime, timezone

from sqlalchemy import select

from app.integrations.salutem.models import ContenidoArchivo
from app.models.audit_log import AuditLog
from app.models.salutem_copia import SalutemArchivo, SalutemAtencion

AHORA = datetime(2026, 10, 15, 20, 0, tzinfo=timezone.utc)
PERSONA = 1180505


def _atencion(db, cita_id, fecha, contenido=None, desaparecida=None):
    db.add(SalutemAtencion(cita_id=cita_id, persona_id=PERSONA, fecha_cita=fecha, contenido=contenido or {},
                           hash_contenido="x", visto_primera_vez=AHORA, visto_ultima_vez=AHORA,
                           cambiado_en=AHORA, desaparecida_en=desaparecida))
    db.flush()


def _archivo(db, archivo_id, creado):
    db.add(SalutemArchivo(archivo_id=archivo_id, persona_id=PERSONA, nombre=f"doc{archivo_id}.pdf",
                          tipo="documento", fecha_creacion=creado, visto_ultima_vez=AHORA))
    db.flush()


EVALUACION = {
    "especialidadNombre": "Evaluación médica",
    "profesionalNombre": "DRA. PAULA ROJAS",
    "antecedentes": [
        {"agrupacion": "Conclusiones", "nombre": "GAF", "registro": {"3": "51-60"}},
        {"agrupacion": "Conclusiones", "nombre": "Indicación de reposo", "registro": "Reposo por 15 días desde el 15/10/2026"},
        {"agrupacion": "Conclusiones", "nombre": "Tipo de reposo", "registro": {"5": "Total"}},
    ],
}


def test_muestra_la_atencion_con_la_indicacion_de_licencia(as_admin, db_session):
    _atencion(db_session, 16625886, date(2026, 10, 15), EVALUACION)

    r = as_admin.get("/api/v1/salutem/atenciones/16625886")

    assert r.status_code == 200, r.text
    assert r.json() == {
        "cita_id": 16625886,
        "fecha": "2026-10-15",
        "especialidad": "Evaluación médica",
        "profesional": "DRA. PAULA ROJAS",
        "indicacion_licencia": "Reposo por 15 días desde el 15/10/2026",
        "tipo_reposo": "Total",
        "gaf_tramo": "51-60",
    }


def test_atencion_inexistente_o_desaparecida_da_404(as_admin, db_session):
    _atencion(db_session, 2, date(2026, 10, 15), desaparecida=AHORA)
    assert as_admin.get("/api/v1/salutem/atenciones/1").status_code == 404
    assert as_admin.get("/api/v1/salutem/atenciones/2").status_code == 404


def test_lista_los_documentos_hasta_la_atencion_siguiente(as_admin, db_session):
    _atencion(db_session, 10, date(2026, 10, 15), EVALUACION)
    _atencion(db_session, 11, date(2026, 10, 17))
    _archivo(db_session, 1, datetime(2026, 10, 15, 16, 29))
    _archivo(db_session, 2, datetime(2026, 10, 17, 9, 0))  # día de la atención siguiente → no
    _archivo(db_session, 3, datetime(2026, 10, 14, 9, 0))  # antes → no

    r = as_admin.get("/api/v1/salutem/atenciones/10/archivos")

    assert [a["archivo_id"] for a in r.json()] == [1]


def test_el_contenido_se_pide_a_salutem_y_se_audita(as_admin, db_session, monkeypatch):
    _atencion(db_session, 10, date(2026, 10, 15), EVALUACION)
    _archivo(db_session, 1, datetime(2026, 10, 15, 16, 29))

    class Cliente:
        def obtener_archivo(self, persona_id, archivo_id):
            assert (persona_id, archivo_id) == (PERSONA, 1)
            return ContenidoArchivo(nombre="licencia.pdf", media_type="application/pdf", datos=b"%PDF")

    monkeypatch.setattr("app.routers.salutem_atenciones.get_salutem_client", lambda: Cliente())

    r = as_admin.get("/api/v1/salutem/atenciones/10/archivos/1/contenido")

    assert r.status_code == 200
    assert r.content == b"%PDF"
    assert db_session.scalars(select(AuditLog).where(AuditLog.entity == "salutem_archivo")).first() is not None
    assert as_admin.get("/api/v1/salutem/atenciones/10/archivos/99/contenido").status_code == 404
