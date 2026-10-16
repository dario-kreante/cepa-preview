"""Lista calculada de pacientes por citar: GET /api/v1/pacientes-por-citar."""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.agendamiento import router as agenda_router
from app.agendamiento.enums import ResultadoGestion
from app.agendamiento.models import DisponibilidadProf, GestionCitacion
from app.domain.enums import EstadoCaso
from app.integrations.salutem.models import EstadoCitaSalutem
from app.models.config_alerta import Festivo
from app.models.control_medico import ControlMedico
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.profesional import Profesional
from app.models.salutem_copia import SalutemCita, SalutemPersona

HOY = date(2026, 10, 16)  # viernes
LUNES = date(2026, 10, 19)
AHORA = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
URL = "/api/v1/pacientes-por-citar"
_seq = {"n": 0}


def _n() -> int:
    _seq["n"] += 1
    return _seq["n"]


@pytest.fixture(autouse=True)
def _hoy_fijo(monkeypatch):
    monkeypatch.setattr(agenda_router, "_hoy", lambda: HOY)


@pytest.fixture
def prof(db_session) -> Profesional:
    p = Profesional(nombre=f"Dra Por Citar {_n()}", origen="SIGE", activo=True)
    db_session.add(p)
    db_session.flush()
    return p


def _cupo(db, prof, dia_semana: int, cupo: int) -> None:
    db.add(DisponibilidadProf(profesional_id=prof.id, dia_semana=dia_semana, cupo_diario=cupo, activo=True))
    db.flush()


def _paciente(db, *, rut: str | None = None, nombre: str | None = None) -> Paciente:
    n = _n()
    p = Paciente(rut=rut, nombre=nombre or f"Paciente PorCitar {n}", sexo="F", edad=40, region="Maule")
    db.add(p)
    db.flush()
    return p


def _ingreso(db, paciente, *, fecha: date = date(2026, 1, 1), estado: str = EstadoCaso.ACTIVO.value,
             folio: str | None = None) -> Ingreso:
    n = _n()
    i = Ingreso(
        paciente_id=paciente.id, folio=folio or f"F-PXC-{n}", folio_manual=True, fecha_ingreso=fecha,
        tipo_derivacion="DIAT", tipo_ingreso="convenio", modelo_tratamiento="ambulatorio",
        diagnostico="test", estado=estado,
    )
    db.add(i)
    db.flush()
    return i


def _control(db, ingreso, prof, *, proximo: date) -> ControlMedico:
    c = ControlMedico(
        ingreso_id=ingreso.id, fecha_control=date(2026, 9, 1), semana_control=1,
        medico_tratante=prof.nombre, region_derivacion="Maule", proximo_control=proximo,
        proximo_agendado=False, tiene_licencia=False, origen="CEPA",
    )
    db.add(c)
    db.flush()
    return c


def _candidato(db, prof, *, vencido: bool = True, rut: str | None = None, nombre: str | None = None,
               folio: str | None = None) -> Paciente:
    """Paciente con ingreso activo y control vencido (P1) o próximo (P2) con este profesional."""
    p = _paciente(db, rut=rut, nombre=nombre)
    proximo = HOY - timedelta(days=5) if vencido else HOY + timedelta(days=3)
    _control(db, _ingreso(db, p, folio=folio), prof, proximo=proximo)
    return p


def _gestion(db, paciente, prof, resultado: ResultadoGestion, creado: datetime) -> GestionCitacion:
    g = GestionCitacion(
        paciente_id=paciente.id, profesional_id=prof.id, resultado=resultado.value,
        nota="llamada", usuario="tester", created_at=creado,
    )
    db.add(g)
    db.flush()
    return g


def _get(cliente, prof, **params):
    return cliente.get(URL, params={"profesional_id": prof.id, **params})


def _ids(body) -> list[int]:
    return [f["paciente_id"] for f in body["pacientes"]]


def test_lista_excluye_paciente_con_hora_vigente_por_rut(as_admin, db_session, prof):
    _cupo(db_session, prof, 1, 5)
    con_hora = _candidato(db_session, prof, rut="123456789")
    sin_hora = _candidato(db_session, prof, rut="987654321")
    db_session.add(SalutemPersona(
        salutem_id=900001, rut="123456789", contenido={}, hash_contenido="h",
        visto_primera_vez=AHORA, visto_ultima_vez=AHORA, cambiado_en=AHORA,
    ))
    db_session.add(SalutemCita(
        cita_id=950001, persona_id=900001, fecha_cita=LUNES, estado_id=int(EstadoCitaSalutem.AGENDADO),
        contenido={}, hash_contenido="h", visto_primera_vez=AHORA, visto_ultima_vez=AHORA,
        cambiado_en=AHORA,
    ))
    db_session.flush()
    r = _get(as_admin, prof, desde=LUNES.isoformat(), hasta=LUNES.isoformat())
    assert r.status_code == 200, r.text
    ids = _ids(r.json())
    assert con_hora.id not in ids
    assert sin_hora.id in ids


def test_lista_secciones_y_dia_sugerido(as_admin, db_session, prof):
    _cupo(db_session, prof, 1, 1)  # lunes, cupo 1
    p1 = _candidato(db_session, prof, vencido=True)
    p2 = _candidato(db_session, prof, vencido=False)
    r = _get(as_admin, prof, desde=LUNES.isoformat(), hasta=LUNES.isoformat())
    assert r.status_code == 200, r.text
    body = r.json()
    filas = {f["paciente_id"]: f for f in body["pacientes"]}
    assert filas[p1.id]["seccion"] == "por_citar"
    assert filas[p1.id]["dia_sugerido"] == LUNES.isoformat()
    assert filas[p1.id]["prioridad"] == "control_vencido"
    assert filas[p2.id]["seccion"] == "sin_cupo"
    assert filas[p2.id]["dia_sugerido"] is None
    assert _ids(body) == [p1.id, p2.id]
    assert body["por_dia"] == [{"fecha": LUNES.isoformat(), "cupo": 1, "asignados": 1}]
    assert body["profesional_id"] == prof.id


def test_lista_oculta_agendada_solo_para_ese_profesional(as_admin, db_session, prof):
    _cupo(db_session, prof, 1, 5)
    otro = Profesional(nombre=f"Dr Otro {_n()}", origen="SIGE", activo=True)
    db_session.add(otro)
    db_session.flush()
    oculto = _candidato(db_session, prof)
    visible = _candidato(db_session, prof)
    reciente = datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc)
    _gestion(db_session, oculto, prof, ResultadoGestion.AGENDADA_EN_SALUTEM, reciente)
    _gestion(db_session, visible, otro, ResultadoGestion.AGENDADA_EN_SALUTEM, reciente)
    r = _get(as_admin, prof, desde=LUNES.isoformat(), hasta=LUNES.isoformat())
    ids = _ids(r.json())
    assert oculto.id not in ids
    assert visible.id in ids


def test_lista_vuelve_tras_3_dias_habiles_con_marca(as_admin, db_session, prof):
    _cupo(db_session, prof, 1, 5)
    antigua = _candidato(db_session, prof)
    reciente = _candidato(db_session, prof)
    # hoy es viernes 16: hace 4 días hábiles = lunes 12; hace 1 día hábil = jueves 15
    _gestion(db_session, antigua, prof, ResultadoGestion.AGENDADA_EN_SALUTEM,
             datetime(2026, 10, 12, 15, 0, tzinfo=timezone.utc))
    _gestion(db_session, reciente, prof, ResultadoGestion.AGENDADA_EN_SALUTEM,
             datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc))
    body = _get(as_admin, prof, desde=LUNES.isoformat(), hasta=LUNES.isoformat()).json()
    filas = {f["paciente_id"]: f for f in body["pacientes"]}
    assert reciente.id not in filas
    assert filas[antigua.id]["dijo_agendada_sin_hora"] is True
    assert filas[antigua.id]["ultima_gestion"]["resultado"] == "agendada_en_salutem"
    assert filas[antigua.id]["ultima_gestion"]["usuario"] == "tester"


def test_lista_feriado_cuenta_para_la_ventana(as_admin, db_session, prof):
    """Con el jueves 15 feriado, la ventana de 3 días hábiles llega hasta el lunes 12 y lo cubre."""
    _cupo(db_session, prof, 1, 5)
    db_session.add(Festivo(fecha=date(2026, 10, 15), descripcion="Feriado de prueba"))
    db_session.flush()
    p = _candidato(db_session, prof)
    _gestion(db_session, p, prof, ResultadoGestion.AGENDADA_EN_SALUTEM,
             datetime(2026, 10, 12, 15, 0, tzinfo=timezone.utc))
    # hábiles hacia atrás desde el vie 16: mié 14, mar 13, lun 12 -> la ventana parte el lunes 12
    body = _get(as_admin, prof, desde=LUNES.isoformat(), hasta=LUNES.isoformat()).json()
    assert p.id not in _ids(body)


def test_lista_gestion_sin_agendada_no_marca(as_admin, db_session, prof):
    _cupo(db_session, prof, 1, 5)
    p = _candidato(db_session, prof)
    _gestion(db_session, p, prof, ResultadoGestion.NO_CONTESTA,
             datetime(2026, 10, 9, 15, 0, tzinfo=timezone.utc))
    fila = _get(as_admin, prof, desde=LUNES.isoformat(), hasta=LUNES.isoformat()).json()["pacientes"][0]
    assert fila["dijo_agendada_sin_hora"] is False
    assert fila["ultima_gestion"]["resultado"] == "no_contesta"


def test_lista_folio_del_ingreso_activo_mas_reciente(as_admin, db_session, prof):
    _cupo(db_session, prof, 1, 5)
    p = _paciente(db_session, nombre="Paciente Folios")
    _ingreso(db_session, p, fecha=date(2025, 1, 1), estado=EstadoCaso.CERRADO.value, folio="F-CERRADO")
    _ingreso(db_session, p, fecha=date(2026, 2, 1), folio="F-ACTIVO-VIEJO")
    nuevo = _ingreso(db_session, p, fecha=date(2026, 6, 1), folio="F-ACTIVO-NUEVO")
    _control(db_session, nuevo, prof, proximo=HOY - timedelta(days=2))
    body = _get(as_admin, prof, desde=LUNES.isoformat(), hasta=LUNES.isoformat()).json()
    fila = next(f for f in body["pacientes"] if f["paciente_id"] == p.id)
    assert fila["folio"] == "F-ACTIVO-NUEVO"
    assert fila["nombre"] == "Paciente Folios"


def test_lista_marca_sin_vinculo_salutem(as_admin, db_session, prof):
    _cupo(db_session, prof, 1, 5)
    sin = _candidato(db_session, prof, rut="111111111")
    con = _candidato(db_session, prof, rut="222222222")
    db_session.add(SalutemPersona(
        salutem_id=900002, rut="222222222", contenido={}, hash_contenido="h",
        visto_primera_vez=AHORA, visto_ultima_vez=AHORA, cambiado_en=AHORA,
    ))
    db_session.flush()
    body = _get(as_admin, prof, desde=LUNES.isoformat(), hasta=LUNES.isoformat()).json()
    filas = {f["paciente_id"]: f for f in body["pacientes"]}
    assert filas[sin.id]["sin_vinculo_salutem"] is True
    assert filas[con.id]["sin_vinculo_salutem"] is False


def test_lista_profesional_inexistente_404_e_inactivo_422(as_admin, db_session, prof):
    assert as_admin.get(URL, params={"profesional_id": 999999999}).status_code == 404
    inactivo = Profesional(nombre=f"Dr Inactivo {_n()}", origen="SIGE", activo=False)
    db_session.add(inactivo)
    db_session.flush()
    assert as_admin.get(URL, params={"profesional_id": inactivo.id}).status_code == 422


def test_lista_rango_invalido_422(as_admin, db_session, prof):
    r = _get(as_admin, prof, desde="2026-10-20", hasta="2026-10-19")
    assert r.status_code == 422
    r = _get(as_admin, prof, desde="2026-10-01", hasta="2026-12-31")
    assert r.status_code == 422


def test_lista_rango_por_defecto_hasta_viernes_siguiente(as_admin, db_session, prof):
    _cupo(db_session, prof, 1, 1)
    body = _get(as_admin, prof).json()
    assert body["desde"] == HOY.isoformat()
    assert body["hasta"] == "2026-10-23"  # viernes de la semana siguiente a la de hoy (vie 16)
    assert [d["fecha"] for d in body["por_dia"]] == ["2026-10-19"]  # lunes: único día con cupo hasta el 23


def test_lista_orden_por_citar_sin_cupo_en_reposo(as_admin, db_session, prof):
    _cupo(db_session, prof, 1, 1)
    p1 = _candidato(db_session, prof, vencido=True)
    p2 = _candidato(db_session, prof, vencido=False)
    p3 = _candidato(db_session, prof, vencido=False)
    body = _get(as_admin, prof, desde=LUNES.isoformat(), hasta=LUNES.isoformat()).json()
    secciones = [f["seccion"] for f in body["pacientes"]]
    assert secciones == ["por_citar", "sin_cupo", "sin_cupo"]
    assert _ids(body)[0] == p1.id
    assert set(_ids(body)[1:]) == {p2.id, p3.id}


def test_lista_auditor_puede_leer(as_auditor, db_session, prof):
    assert _get(as_auditor, prof).status_code == 200


def test_lista_sin_token_401(client, prof):
    assert client.get(URL, params={"profesional_id": prof.id}).status_code == 401
