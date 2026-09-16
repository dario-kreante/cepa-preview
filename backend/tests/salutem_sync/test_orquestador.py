from datetime import date, timedelta

from sqlalchemy import select

from app.integrations.salutem.client import SalutemStubClient
from app.integrations.salutem.models import EstadoCitaSalutem
from app.models.ficha_clinica import FichaClinica
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.salutem_sync import SalutemSyncEjecucion, SalutemSyncLease
from app.services.salutem_sync import orquestador
from app.services.salutem_sync.lease import tomar_lease
from app.services.salutem_sync.orquestador import Opciones, correr
from app.services.salutem_sync.vinculacion import ResultadoVinculacion
from tests.salutem_sync.conftest import AHORA

HOY = date(2026, 9, 16)


def _ejecuciones(db, modo):
    return db.scalars(
        select(SalutemSyncEjecucion).where(SalutemSyncEjecucion.modo == modo).order_by(SalutemSyncEjecucion.id)
    ).all()


def _correr(db, salutem, ritmo, modo="caliente", **kw):
    return correr(modo, db, salutem, ritmo, ahora=lambda: AHORA, habilitado=kw.pop("habilitado", True), dueno="test", **kw)


def test_apagado_no_hace_nada(db_session, salutem, ritmo):
    assert _correr(db_session, salutem, ritmo, habilitado=False) == 0
    assert salutem.llamadas == []
    assert _ejecuciones(db_session, "caliente") == []


def test_sin_credenciales_termina_con_error(db_session, ritmo):
    assert correr("caliente", db_session, SalutemStubClient(), ritmo, ahora=lambda: AHORA, habilitado=True) == 2


def test_con_el_lease_ocupado_queda_omitida(db_session, salutem, ritmo):
    assert tomar_lease(db_session, "otro-proceso", AHORA)

    assert _correr(db_session, salutem, ritmo) == 0

    assert [e.estado for e in _ejecuciones(db_session, "caliente")] == ["omitida"]
    assert salutem.llamadas == []


def test_caliente_exitosa_registra_bitacora_y_suelta_el_lease(db_session, salutem, ritmo):
    assert _correr(db_session, salutem, ritmo) == 0

    (ejecucion,) = _ejecuciones(db_session, "caliente")
    assert ejecucion.estado == "ok"
    assert ejecucion.llamadas == 27  # 3 días × 9 estados
    assert db_session.get(SalutemSyncLease, "salutem").dueno is None


def test_credencial_rechazada_deja_error_y_suelta_el_lease(db_session, salutem, ritmo):
    salutem.credencial_rechazada = True

    assert _correr(db_session, salutem, ritmo) == 1

    (ejecucion,) = _ejecuciones(db_session, "caliente")
    assert ejecucion.estado == "error"
    assert "SalutemAuthError" in ejecucion.error
    assert db_session.get(SalutemSyncLease, "salutem").dueno is None


def test_dias_con_error_quedan_como_con_errores(db_session, salutem, ritmo):
    salutem.dias_con_error.add((HOY, int(EstadoCitaSalutem.ATENDIDO)))
    assert _correr(db_session, salutem, ritmo) == 0
    (ejecucion,) = _ejecuciones(db_session, "caliente")
    assert ejecucion.estado == "con_errores"
    assert "ERROR_INTERVALO_SUPERADO" in ejecucion.error


def test_al_terminar_vincula_con_el_dominio_cepa(db_session, salutem, ritmo):
    p = Paciente(rut="123456785", nombre="Orquestador", sexo="F", edad=33, region="Maule")
    db_session.add(p)
    db_session.flush()
    db_session.add(
        Ingreso(
            paciente_id=p.id, folio="F-ORQ-1", folio_manual=True, fecha_ingreso=HOY - timedelta(days=30),
            tipo_derivacion="DIAT", tipo_ingreso="convenio", modelo_tratamiento="ambulatorio",
            diagnostico="orquestador", estado="activo",
        )
    )
    db_session.flush()
    salutem.agregar_persona(501, "12345678-5")
    salutem.agregar_cita(9001, 501, HOY)
    salutem.agregar_atencion(9001, anamnesis="de hoy")

    assert _correr(db_session, salutem, ritmo) == 0

    ficha = db_session.scalars(select(FichaClinica).where(FichaClinica.folio == "F-ORQ-1")).one()
    assert ficha.salutem_cita_id == 9001


def test_backfill_usa_las_opciones(db_session, salutem, ritmo):
    opciones = Opciones(desde=HOY - timedelta(days=1), verificar=False, dias_futuro=0)
    assert _correr(db_session, salutem, ritmo, modo="backfill", opciones=opciones) == 0
    assert _ejecuciones(db_session, "backfill")[0].llamadas == 18


def test_vincular_no_llama_a_salutem(db_session, salutem, ritmo):
    assert _correr(db_session, salutem, ritmo, modo="vincular", opciones=Opciones(vincular_todo=True)) == 0
    assert salutem.llamadas == []
    assert _ejecuciones(db_session, "vincular")[0].estado == "ok"


def test_si_pierde_el_lease_termina_en_error_sin_soltar_el_ajeno(db_session, salutem, ritmo, monkeypatch):
    llamadas = []

    def tomar_una_vez(db, dueno, ahora):
        llamadas.append(dueno)
        if len(llamadas) == 1:
            return tomar_lease(db, dueno, ahora)
        # Otro proceso lo tomó mientras este trabajaba.
        tomar_lease(db, "intruso", AHORA + timedelta(hours=1))
        return False

    monkeypatch.setattr(orquestador, "tomar_lease", tomar_una_vez)

    assert _correr(db_session, salutem, ritmo, modo="vincular") == 1

    (ejecucion,) = _ejecuciones(db_session, "vincular")
    assert ejecucion.estado == "error"
    assert "LeasePerdidoError" in ejecucion.error
    assert db_session.get(SalutemSyncLease, "salutem").dueno == "intruso"


def test_errores_de_vinculacion_dejan_la_ejecucion_con_errores(db_session, salutem, ritmo, monkeypatch):
    def vincular_con_error(*args, **kwargs):
        return ResultadoVinculacion(errores=["cita 9001: RuntimeError: x"])

    monkeypatch.setattr(orquestador, "vincular", vincular_con_error)

    assert _correr(db_session, salutem, ritmo, modo="vincular") == 0

    (ejecucion,) = _ejecuciones(db_session, "vincular")
    assert ejecucion.estado == "con_errores"
    assert "cita 9001" in ejecucion.error


def test_si_falla_al_abrir_la_bitacora_suelta_el_lease(db_session, salutem, ritmo, monkeypatch):
    def abrir_que_falla(*args, **kwargs):
        raise RuntimeError("bitácora caída")

    monkeypatch.setattr(orquestador, "abrir_ejecucion", abrir_que_falla)

    assert _correr(db_session, salutem, ritmo) == 1
    assert db_session.get(SalutemSyncLease, "salutem").dueno is None
