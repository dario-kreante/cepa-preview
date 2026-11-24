"""QA-003 (23-11-2026): la ficha conserva y completa los datos de contacto de SALUTEM."""

from app.domain.comunas import buscar_comuna, codigo_region, region_de_comuna
from app.models.paciente import Paciente
from app.services.salutem_sync.borradores import completar_contacto
from tests.salutem_sync.test_borradores import _persona
from tests.test_ingreso_completar_borrador import _borrador, _payload


def test_region_de_comuna_sin_tildes_ni_mayusculas():
    assert region_de_comuna("TALCA") == "Maule"
    assert region_de_comuna("concepcion") == "Biobío"
    assert region_de_comuna("Comuna inventada") is None
    assert region_de_comuna(None) is None
    assert buscar_comuna("Santiago") == ("13101", "Santiago", "13")
    assert codigo_region("Biobio") == "08"


def test_completar_el_borrador_no_borra_el_contacto_de_salutem(as_admin, db_session):
    p = _borrador(db_session, comuna="Talca", telefono="+56912345678", correo="ana@correo.cl")

    r = as_admin.post("/api/v1/ingresos", json=_payload(paciente_id=p.id))

    assert r.status_code == 201, r.text
    db_session.expire_all()
    p = db_session.get(Paciente, p.id)
    assert (p.comuna, p.telefono, p.correo) == ("Talca", "+56912345678", "ana@correo.cl")


def test_completar_contacto_rellena_solo_lo_vacio(db_session):
    _persona(db_session, 7200, identificacion="12345678-5", comuna="Curicó",
             telefonoMovil="+56911112222", email="nuevo@correo.cl")
    vacio = Paciente(nombre="ANA", rut="123456785", estado_registro="completo")
    con_datos = Paciente(nombre="BEA", rut=None, salutem_persona_id=7200, estado_registro="completo",
                         region="Ñuble", comuna="Chillán", telefono="+56900000000", correo="bea@x.cl")
    db_session.add_all([vacio, con_datos])
    db_session.flush()

    assert completar_contacto(db_session) == 1

    assert (vacio.comuna, vacio.telefono, vacio.correo, vacio.region) == (
        "Curicó", "+56911112222", "nuevo@correo.cl", "Maule")
    assert (con_datos.region, con_datos.comuna, con_datos.telefono, con_datos.correo) == (
        "Ñuble", "Chillán", "+56900000000", "bea@x.cl")
    assert completar_contacto(db_session) == 0
