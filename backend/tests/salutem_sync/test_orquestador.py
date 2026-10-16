from datetime import date, timedelta

from sqlalchemy import select

from app.integrations.salutem.client import SalutemStubClient
from app.integrations.salutem.models import EstadoCitaSalutem
from app.models.cita import Cita
from app.models.ficha_clinica import FichaClinica
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.salutem_sync import SalutemSyncEjecucion, SalutemSyncLease
from app.services.salutem_sync import orquestador
from app.services.salutem_sync.archivos import ResultadoArchivos
from app.services.salutem_sync.bitacora import ultimo_inicio_ok
from app.services.salutem_sync.borradores import ResultadoBorradores
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


def test_un_modo_manual_omitido_por_lease_lo_informa_en_el_codigo_de_salida(db_session, ritmo):
    """`vincular` y `backfill` se corren a mano: si otro proceso tiene el lease no hicieron
    nada, y eso tiene que notarse (código OMITIDO) en vez de parecer un éxito."""
    assert tomar_lease(db_session, "otro-proceso", AHORA)

    codigo = correr("vincular", db_session, SalutemStubClient(), ritmo, ahora=lambda: AHORA, habilitado=True)

    assert codigo == orquestador.OMITIDO


def test_caliente_copia_la_biblioteca_despues_de_vincular(db_session, salutem, ritmo, monkeypatch):
    llamadas = []

    def falso(db, cliente, ritmo, ahora, al_avanzar):
        al_avanzar()  # renueva el lease: no debe levantar mientras el lease sea nuestro
        llamadas.append(ahora)
        return ResultadoArchivos()

    monkeypatch.setattr("app.services.salutem_sync.orquestador.refrescar_archivos", falso)
    assert _correr(db_session, salutem, ritmo, modo="caliente") == 0
    assert llamadas == [AHORA]


def test_tibia_no_copia_la_biblioteca(db_session, salutem, ritmo, monkeypatch):
    llamadas = []
    monkeypatch.setattr(
        "app.services.salutem_sync.orquestador.refrescar_archivos",
        lambda *a: llamadas.append(a) or ResultadoArchivos(),
    )
    assert _correr(db_session, salutem, ritmo, modo="tibia") == 0
    assert llamadas == []


def test_cada_modo_crea_borradores_despues_de_vincular(db_session, salutem, ritmo, monkeypatch):
    llamadas = []
    monkeypatch.setattr(
        orquestador, "crear_borradores",
        lambda db, ahora, desde: llamadas.append(ahora) or ResultadoBorradores(),
    )

    for modo in ("caliente", "tibia"):
        assert _correr(db_session, salutem, ritmo, modo=modo) == 0

    assert llamadas == [AHORA, AHORA]


def _paciente_con_ingreso(db, folio="F-ORQ-CIT"):
    p = Paciente(rut="123456785", nombre="Orquestador citas", sexo="F", edad=33, region="Maule")
    db.add(p)
    db.flush()
    db.add(
        Ingreso(
            paciente_id=p.id, folio=folio, folio_manual=True, fecha_ingreso=HOY - timedelta(days=60),
            tipo_derivacion="DIAT", tipo_ingreso="convenio", modelo_tratamiento="ambulatorio",
            diagnostico="orquestador", estado="activo",
        )
    )
    db.flush()


def _citas_salutem(db):
    return db.scalars(select(Cita).where(Cita.salutem_cita_id.is_not(None))).all()


def test_orquestador_corre_paso_de_citas(db_session, salutem, ritmo):
    _paciente_con_ingreso(db_session)
    salutem.agregar_persona(501, "12345678-5")
    salutem.agregar_cita(9001, 501, HOY)

    assert _correr(db_session, salutem, ritmo) == 0

    (cita,) = _citas_salutem(db_session)
    assert cita.salutem_cita_id == 9001
    assert cita.origen == "SALUTEM"


def test_orquestador_backfill_revisa_todo(db_session, salutem, ritmo, monkeypatch):
    recibidos = []
    real = orquestador.sincronizar_citas

    def espiar(db, *, desde, ahora, al_avanzar):
        recibidos.append(desde)
        return real(db, desde=desde, ahora=ahora, al_avanzar=al_avanzar)

    monkeypatch.setattr(orquestador, "sincronizar_citas", espiar)
    opciones = Opciones(desde=HOY - timedelta(days=1), verificar=False, dias_futuro=0)

    assert _correr(db_session, salutem, ritmo, modo="backfill", opciones=opciones) == 0
    assert recibidos == [None]

    # Un modo incremental, con una ejecución previa exitosa, sí acota con `desde`.
    assert _correr(db_session, salutem, ritmo) == 0
    assert recibidos[0] is None and recibidos[1] is not None


def test_fallo_en_citas_no_pierde_el_ciclo(db_session, salutem, ritmo, monkeypatch):
    def explotar(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(orquestador, "sincronizar_citas", explotar)

    assert _correr(db_session, salutem, ritmo) == 0

    (ejecucion,) = _ejecuciones(db_session, "caliente")
    assert ejecucion.estado == "con_errores"
    assert "citas: RuntimeError: boom" in ejecucion.error
    assert db_session.get(SalutemSyncLease, "salutem").dueno is None


def test_citas_no_avanza_su_desde_tras_una_ejecucion_con_errores(db_session, salutem, ritmo, monkeypatch):
    recibidos = []
    real = orquestador.sincronizar_citas

    def espiar(db, *, desde, ahora, al_avanzar):
        recibidos.append(desde)
        return real(db, desde=desde, ahora=ahora, al_avanzar=al_avanzar)

    monkeypatch.setattr(orquestador, "sincronizar_citas", espiar)
    # Una ejecución `ok` previa fija el punto de partida de las citas.
    previa = SalutemSyncEjecucion(
        modo="caliente", estado="ok", inicio=AHORA - timedelta(hours=3),
        fin=AHORA - timedelta(hours=3), llamadas=0, nuevos=0, cambiados=0, desaparecidos=0,
    )
    # Y una posterior con errores no debe adelantarlo.
    con_errores = SalutemSyncEjecucion(
        modo="caliente", estado="con_errores", inicio=AHORA - timedelta(hours=1),
        fin=AHORA - timedelta(hours=1), llamadas=0, nuevos=0, cambiados=0, desaparecidos=0,
    )
    db_session.add_all([previa, con_errores])
    db_session.flush()

    assert _correr(db_session, salutem, ritmo) == 0

    assert recibidos == [previa.inicio]
    assert ultimo_inicio_ok(db_session) == AHORA  # la corrida limpia sí lo adelanta
