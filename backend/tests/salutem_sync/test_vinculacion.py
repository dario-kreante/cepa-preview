from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.integrations.salutem.models import AtencionSalutem, PersonaSalutem
from app.models.audit_log import AuditLog
from app.models.ficha_clinica import FichaClinica
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemAtencion
from app.services.salutem_sync import copia, vinculacion
from app.services.salutem_sync.vinculacion import ACTOR, vincular
from tests.salutem_sync.conftest import AHORA

RUT_SALUTEM = "12.345.678-5"
RUT_CEPA = "123456785"


def _copiar(db, *, cita_id=9001, persona_id=501, fecha=date(2026, 2, 10), **contenido):
    copia.guardar_persona(
        db, PersonaSalutem.desde_api({"SALUTEM_ID": persona_id, "identificacion": RUT_SALUTEM}), AHORA
    )
    crudo = {"personaId": persona_id, "citaId": cita_id, "citaFecha": fecha.isoformat(), **contenido}
    copia.guardar_atencion(db, AtencionSalutem.desde_api(crudo), AHORA)


def _paciente(db) -> Paciente:
    p = Paciente(rut=RUT_CEPA, nombre="Paciente Sync", sexo="F", edad=40, region="Maule")
    db.add(p)
    db.flush()
    return p


def _ingreso(db, paciente, folio="F-SYNC-1", desde=date(2026, 1, 1), alta=None) -> Ingreso:
    ingreso = Ingreso(
        paciente_id=paciente.id, folio=folio, folio_manual=True, fecha_ingreso=desde,
        fecha_alta=alta, tipo_derivacion="DIAT", tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio", diagnostico="test sync", estado="activo",
    )
    db.add(ingreso)
    db.flush()
    return ingreso


def _fichas(db) -> list[FichaClinica]:
    return list(db.scalars(select(FichaClinica).where(FichaClinica.salutem_cita_id.is_not(None))).all())


def test_crea_la_ficha_para_una_atencion_dentro_de_la_ventana(db_session):
    ingreso = _ingreso(db_session, _paciente(db_session))
    _copiar(db_session, anamnesis="hola")

    r = vincular(db_session, AHORA)

    fichas = _fichas(db_session)
    assert r.fichas_nuevas == 1
    assert len(fichas) == 1
    assert (fichas[0].ingreso_id, fichas[0].folio, fichas[0].origen) == (ingreso.id, "F-SYNC-1", "SALUTEM")
    assert fichas[0].salutem_cita_id == 9001
    assert fichas[0].contenido["anamnesis"] == "hola"
    atencion = db_session.get(SalutemAtencion, 9001)
    assert atencion.hash_vinculado == atencion.hash_contenido
    assert db_session.scalars(select(AuditLog).where(AuditLog.actor == ACTOR)).first() is not None


def test_sin_paciente_cepa_queda_pendiente_hasta_que_exista(db_session):
    _copiar(db_session)

    assert vincular(db_session, AHORA).fichas_nuevas == 0
    assert db_session.get(SalutemAtencion, 9001).hash_vinculado is None

    _ingreso(db_session, _paciente(db_session))
    assert vincular(db_session, AHORA).fichas_nuevas == 1


def test_fuera_de_la_ventana_del_ingreso_no_crea_ficha(db_session):
    _ingreso(db_session, _paciente(db_session), desde=date(2026, 3, 1))
    _copiar(db_session, fecha=date(2026, 2, 10))

    r = vincular(db_session, AHORA)

    assert r.fichas_nuevas == 0
    assert r.atenciones_revisadas == 1


def test_vincular_dos_veces_no_duplica(db_session):
    _ingreso(db_session, _paciente(db_session))
    _copiar(db_session)

    vincular(db_session, AHORA, todo=True)
    r = vincular(db_session, AHORA, todo=True)

    assert (r.fichas_nuevas, r.fichas_actualizadas) == (0, 0)
    assert len(_fichas(db_session)) == 1


def test_contenido_editado_en_salutem_actualiza_la_ficha(db_session):
    _ingreso(db_session, _paciente(db_session))
    _copiar(db_session, anamnesis="inicial")
    vincular(db_session, AHORA)

    _copiar(db_session, anamnesis="editada")
    r = vincular(db_session, AHORA)

    assert r.fichas_actualizadas == 1
    assert _fichas(db_session)[0].contenido["anamnesis"] == "editada"


def test_atencion_desaparecida_marca_la_ficha_sin_borrarla(db_session):
    _ingreso(db_session, _paciente(db_session))
    _copiar(db_session)
    vincular(db_session, AHORA)

    copia.marcar_atencion_desaparecida(db_session, 9001, AHORA)
    r = vincular(db_session, AHORA)

    assert r.fichas_eliminadas == 1
    assert _fichas(db_session)[0].eliminada_en_origen is not None


def test_un_ingreso_nuevo_recibe_atenciones_ya_vinculadas(db_session):
    paciente = _paciente(db_session)
    _copiar(db_session)
    vincular(db_session, AHORA)  # el paciente existe pero no tiene ingreso: nada que crear
    assert db_session.get(SalutemAtencion, 9001).hash_vinculado is not None

    _ingreso(db_session, paciente)
    hace_un_rato = datetime.now(timezone.utc) - timedelta(minutes=5)
    r = vincular(db_session, AHORA, ingresos_desde=hace_un_rato)

    assert r.fichas_nuevas == 1


def test_vincular_avisa_en_cada_lote_para_renovar_el_lease(db_session):
    _ingreso(db_session, _paciente(db_session))
    _copiar(db_session)
    avisos = []

    vincular(db_session, AHORA, lote=1, al_avanzar=lambda: avisos.append(1))

    assert avisos


def test_una_atencion_que_falla_no_bloquea_a_las_demas(db_session, monkeypatch):
    ingreso = _ingreso(db_session, _paciente(db_session))
    _copiar(db_session, cita_id=9001)
    _copiar(db_session, cita_id=9002)
    aplicar_real = vinculacion._aplicar

    def aplicar_que_falla(db, atencion, *args, **kwargs):
        if atencion.cita_id == 9001:
            raise RuntimeError("contenido corrupto")
        return aplicar_real(db, atencion, *args, **kwargs)

    monkeypatch.setattr(vinculacion, "_aplicar", aplicar_que_falla)

    r = vincular(db_session, AHORA)

    assert [f.salutem_cita_id for f in _fichas(db_session)] == [9002]
    assert _fichas(db_session)[0].ingreso_id == ingreso.id
    assert db_session.get(SalutemAtencion, 9001).hash_vinculado is None
    assert db_session.get(SalutemAtencion, 9002).hash_vinculado is not None
    assert len(r.errores) == 1
    assert "cita 9001: RuntimeError" in r.errores[0]
    assert r.fichas_nuevas == 1


def test_ingresos_superpuestos_reciben_una_ficha_cada_uno_sin_duplicar(db_session):
    paciente = _paciente(db_session)
    uno = _ingreso(db_session, paciente, folio="F-SYNC-1", desde=date(2026, 1, 1))
    dos = _ingreso(db_session, paciente, folio="F-SYNC-2", desde=date(2026, 2, 1))
    _copiar(db_session, fecha=date(2026, 2, 10))

    primera = vincular(db_session, AHORA, todo=True)
    segunda = vincular(db_session, AHORA, todo=True)

    assert primera.fichas_nuevas == 2
    assert sorted(f.ingreso_id for f in _fichas(db_session)) == sorted([uno.id, dos.id])
    assert segunda.fichas_nuevas == 0
    assert len(_fichas(db_session)) == 2


def test_ingresos_desde_no_revisa_pacientes_con_ingresos_anteriores_al_corte(db_session):
    _ingreso(db_session, _paciente(db_session))
    _copiar(db_session)
    vincular(db_session, AHORA)

    corte = datetime.now(timezone.utc) + timedelta(minutes=5)
    r = vincular(db_session, AHORA, ingresos_desde=corte)

    assert r.atenciones_revisadas == 0
