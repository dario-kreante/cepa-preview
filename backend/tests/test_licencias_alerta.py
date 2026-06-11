import datetime

import pytest

from app.models.alerta_licencia import AlertaLicencia
from app.models.ingreso import Ingreso
from app.models.licencia import LicenciaMedica
from app.models.paciente import Paciente
from app.services.licencias_alerta import contar_dias_habiles, generar_alertas_vencimiento


def _make_lm(db, termino: datetime.date, anulada: bool = False) -> LicenciaMedica:
    pac = Paciente(
        rut=f"9{termino.toordinal()}", nombre="Alerta Test", sexo="M", edad=40, region="RM"
    )
    db.add(pac)
    db.flush()
    ing = Ingreso(
        paciente_id=pac.id,
        folio=f"F-ALRT-{termino.isoformat()}",
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
    inicio = termino - datetime.timedelta(days=14)
    lm = LicenciaMedica(
        ingreso_id=ing.id,
        tipo_lm="5",
        tipo_reposo="total",
        fecha_inicio=inicio,
        fecha_termino=termino,
        fecha_emision=inicio,
        inicio_reposo=inicio,
        fin_reposo=termino,
        cantidad_dias=15,
        diagnostico="F32.1",
        origen="sistema",
        envio_isl="pendiente",
        anulada=anulada,
    )
    db.add(lm)
    db.flush()
    return lm


# Pruebas unitarias puras de contar_dias_habiles (sin BD)
# TC-072-02: cálculo correcto saltando fin de semana
def test_contar_dias_habiles_salta_fin_de_semana():
    # viernes 05/06/2026 -> lunes 08/06, martes 09/06, miércoles 10/06
    # (Jun 6=sábado, Jun 7=domingo se saltan)
    viernes = datetime.date(2026, 6, 5)   # viernes real
    lunes = datetime.date(2026, 6, 8)     # lunes
    martes = datetime.date(2026, 6, 9)    # martes
    miercoles = datetime.date(2026, 6, 10)  # miércoles
    assert contar_dias_habiles(viernes, lunes) == 1
    assert contar_dias_habiles(viernes, martes) == 2
    assert contar_dias_habiles(viernes, miercoles) == 3


def test_contar_dias_habiles_mismo_dia_es_cero():
    hoy = datetime.date(2026, 6, 10)
    assert contar_dias_habiles(hoy, hoy) == 0


def test_contar_dias_habiles_fin_en_pasado_es_negativo():
    hoy = datetime.date(2026, 6, 10)
    ayer = datetime.date(2026, 6, 9)
    assert contar_dias_habiles(hoy, ayer) < 0


# TC-072-01: LM vence exactamente en 3 días hábiles -> alerta generada
def test_lm_vence_en_3_habiles_genera_alerta(db_session):
    # Hoy = miércoles 10/06/2026; 3 días hábiles después = lunes 15/06/2026
    hoy = datetime.date(2026, 6, 10)
    termino = datetime.date(2026, 6, 15)
    lm = _make_lm(db_session, termino)
    db_session.flush()

    generadas = generar_alertas_vencimiento(db_session, hoy=hoy, umbral_habiles=3)

    assert lm.id in [a.licencia_id for a in generadas]


# TC-072-03: LM vencida no genera alerta
def test_lm_vencida_no_genera_alerta(db_session):
    hoy = datetime.date(2026, 6, 10)
    termino = datetime.date(2026, 6, 9)  # ayer → vencida
    lm = _make_lm(db_session, termino)
    db_session.flush()

    generadas = generar_alertas_vencimiento(db_session, hoy=hoy, umbral_habiles=3)

    assert lm.id not in [a.licencia_id for a in generadas]


# TC-072-04: idempotencia — segunda ejecución no duplica alerta
def test_no_duplica_alerta_si_ya_existe(db_session):
    hoy = datetime.date(2026, 6, 10)
    termino = datetime.date(2026, 6, 13)  # 3 días hábiles (jue)
    lm = _make_lm(db_session, termino)
    db_session.flush()

    primera = generar_alertas_vencimiento(db_session, hoy=hoy, umbral_habiles=3)
    segunda = generar_alertas_vencimiento(db_session, hoy=hoy, umbral_habiles=3)

    alertas_de_lm = [a for a in primera if a.licencia_id == lm.id]
    alertas_segunda = [a for a in segunda if a.licencia_id == lm.id]
    # segunda ejecución no genera nuevas (devuelve lista vacía para esa LM)
    assert len(alertas_de_lm) == 1
    assert len(alertas_segunda) == 0


# LM anulada no genera alerta (RN-5 CEPA-072)
def test_lm_anulada_no_genera_alerta(db_session):
    hoy = datetime.date(2026, 6, 10)
    termino = datetime.date(2026, 6, 13)
    lm = _make_lm(db_session, termino, anulada=True)
    db_session.flush()

    generadas = generar_alertas_vencimiento(db_session, hoy=hoy, umbral_habiles=3)

    assert lm.id not in [a.licencia_id for a in generadas]
