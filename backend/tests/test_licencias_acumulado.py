import datetime

import pytest

from app.models.licencia import LicenciaMedica
from app.models.paciente import Paciente
from app.models.ingreso import Ingreso
from app.services.licencias_acumulado import calcular_acumulado


def _make_ingreso(db) -> Ingreso:
    """Crea paciente + ingreso de prueba y devuelve el ingreso."""
    pac = Paciente(rut="201010101", nombre="Test Licencias", sexo="F", edad=35, region="Maule")
    db.add(pac)
    db.flush()
    ing = Ingreso(
        paciente_id=pac.id,
        folio="F-TEST-0001",
        folio_manual=True,
        fecha_ingreso=datetime.date(2026, 1, 1),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="F32",
        estado="activo",
    )
    db.add(ing)
    db.flush()
    return ing


def _lm(ingreso_id, inicio, termino, dias, origen="sistema", anulada=False):
    return LicenciaMedica(
        ingreso_id=ingreso_id,
        tipo_lm="1",
        tipo_reposo="total",
        fecha_inicio=inicio,
        fecha_termino=termino,
        fecha_emision=inicio,
        inicio_reposo=inicio,
        fin_reposo=termino,
        cantidad_dias=dias,
        diagnostico="F32.1",
        origen=origen,
        envio_isl="pendiente",
        anulada=anulada,
    )


# RN-6 CEPA-071: paciente sin LM previas -> acumulado = días primera LM
# TC-071-02
def test_primera_lm_acumulado_igual_a_sus_dias(db_session):
    ing = _make_ingreso(db_session)
    lm = _lm(ing.id, datetime.date(2026, 6, 1), datetime.date(2026, 6, 12), 12)
    db_session.add(lm)
    db_session.flush()

    resultado = calcular_acumulado(db_session, ing.id)

    assert resultado.dias_acumulados_vigentes == 12
    assert resultado.dias_acumulados_bruto == 12
    assert resultado.hay_solapamiento is False


# CA-1 CEPA-071: 3 LM previas + 1 nueva = suma total
# TC-071-01
def test_cuatro_lm_sin_solapamiento_suma_correcta(db_session):
    ing = _make_ingreso(db_session)
    for inicio, termino, dias in [
        (datetime.date(2026, 1, 1), datetime.date(2026, 1, 10), 10),
        (datetime.date(2026, 2, 1), datetime.date(2026, 2, 15), 15),
        (datetime.date(2026, 3, 1), datetime.date(2026, 3, 7), 7),
        (datetime.date(2026, 4, 1), datetime.date(2026, 4, 8), 8),
    ]:
        db_session.add(_lm(ing.id, inicio, termino, dias))
    db_session.flush()

    resultado = calcular_acumulado(db_session, ing.id)

    assert resultado.dias_acumulados_bruto == 40
    assert resultado.dias_acumulados_vigentes == 40
    assert resultado.hay_solapamiento is False


# RN-3 CEPA-071: solapamiento — días calendario efectivos no duplican
# TC-071-03: LM A=01–10/jun, LM B=06–15/jun → solapamiento 06–10 (5 días)
def test_solapamiento_no_duplica_dias(db_session):
    ing = _make_ingreso(db_session)
    # LM A: 01/06 – 10/06 = 10 días calendario efectivos (01..10)
    db_session.add(_lm(ing.id, datetime.date(2026, 6, 1), datetime.date(2026, 6, 10), 10))
    # LM B: 06/06 – 15/06 = 10 días calendario efectivos (06..15)
    db_session.add(_lm(ing.id, datetime.date(2026, 6, 6), datetime.date(2026, 6, 15), 10))
    db_session.flush()

    resultado = calcular_acumulado(db_session, ing.id)

    # bruto = 10 + 10 = 20 (suma simple)
    assert resultado.dias_acumulados_bruto == 20
    # efectivos: días únicos entre 01/06..10/06 ∪ 06/06..15/06 = 01..15 = 15 días
    assert resultado.dias_acumulados_vigentes == 15
    assert resultado.hay_solapamiento is True


# TC-071-04: LM extra-sistema suma al acumulado marcada como tal
def test_extra_sistema_suma_al_acumulado(db_session):
    ing = _make_ingreso(db_session)
    db_session.add(_lm(ing.id, datetime.date(2026, 1, 1), datetime.date(2026, 1, 20), 20, origen="extra_sistema"))
    db_session.add(_lm(ing.id, datetime.date(2026, 2, 1), datetime.date(2026, 2, 10), 10))
    db_session.flush()

    resultado = calcular_acumulado(db_session, ing.id)

    assert resultado.dias_acumulados_vigentes == 30
    assert resultado.incluye_extra_sistema is True


# TC-071-05 / RN-4: LM anulada se excluye del acumulado vigente
def test_lm_anulada_excluida_del_acumulado(db_session):
    ing = _make_ingreso(db_session)
    db_session.add(_lm(ing.id, datetime.date(2026, 1, 1), datetime.date(2026, 1, 15), 15))
    # esta se anula (77 BIS)
    db_session.add(_lm(ing.id, datetime.date(2026, 2, 1), datetime.date(2026, 2, 15), 15, anulada=True))
    db_session.flush()

    resultado = calcular_acumulado(db_session, ing.id)

    assert resultado.dias_acumulados_vigentes == 15
    assert resultado.dias_acumulados_bruto == 15


# Borde: ingreso sin LM -> acumulado = 0
def test_ingreso_sin_lm_acumulado_cero(db_session):
    ing = _make_ingreso(db_session)
    resultado = calcular_acumulado(db_session, ing.id)
    assert resultado.dias_acumulados_vigentes == 0
    assert resultado.hay_solapamiento is False
