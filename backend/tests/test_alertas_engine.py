"""Tests unitarios del motor puro de evaluación de plazos (CEPA-100).

No requieren BD ni red — el motor es una función pura.
Cubre CA-1..CA-8, TC-100-01..TC-100-07.
"""

from datetime import date, timedelta


from app.services.alertas import (
    HitoPlazos,
    dias_habiles_hasta,
    evaluar_plazos,
)


# ---------------------------------------------------------------------------
# Helper: dias_habiles_hasta
# ---------------------------------------------------------------------------


def test_dias_habiles_excluye_sabado_y_domingo():
    # lunes 2026-06-08 → viernes 2026-06-12: 4 días hábiles (mar, mie, jue, vie)
    lunes = date(2026, 6, 8)
    viernes = date(2026, 6, 12)
    assert dias_habiles_hasta(lunes, viernes) == 4


def test_dias_habiles_plazo_en_fin_de_semana(
    # TC-100-06: licencia que vence viernes, ventana 3d hábiles
    # Si hoy es martes 2026-06-09, el viernes 2026-06-12 está a 3 días hábiles (mie, jue, vie)
):
    hoy = date(2026, 6, 9)   # martes
    viernes = date(2026, 6, 12)  # viernes
    assert dias_habiles_hasta(hoy, viernes) == 3


def test_dias_habiles_misma_fecha():
    hoy = date(2026, 6, 10)
    assert dias_habiles_hasta(hoy, hoy) == 0


def test_dias_habiles_plazo_pasado():
    hoy = date(2026, 6, 10)
    ayer = date(2026, 6, 9)
    # plazo ya pasado → días negativos o cero; el motor no genera alerta de plazo pasado
    assert dias_habiles_hasta(hoy, ayer) < 0


# ---------------------------------------------------------------------------
# evaluar_plazos — casos positivos (CA-1..CA-6)
# ---------------------------------------------------------------------------


def test_genera_alerta_vencimiento_licencia_dentro_de_ventana():
    # TC-100-01: licencia que vence en 2 días hábiles, ventana 3 → debe generar alerta
    hoy = date(2026, 6, 9)  # martes
    vencimiento = date(2026, 6, 11)  # jueves (2 días hábiles)
    hitos = [
        HitoPlazos(
            tipo="vencimiento_licencia",
            caso_id=1,
            caso_tipo="licencia",
            usuario_id=10,
            plazo_objetivo=vencimiento,
            ventana_dias=3,
            usar_dias_habiles=True,
        )
    ]
    resultados = evaluar_plazos(hitos, hoy=hoy)
    assert len(resultados) == 1
    assert resultados[0].tipo == "vencimiento_licencia"
    assert resultados[0].caso_id == 1
    assert resultados[0].usuario_id == 10


def test_no_genera_alerta_fuera_de_ventana():
    # TC-100-04: licencia que vence en 30 días → fuera de ventana de 3 días hábiles
    hoy = date(2026, 6, 9)
    vencimiento = hoy + timedelta(days=30)
    hitos = [
        HitoPlazos(
            tipo="vencimiento_licencia",
            caso_id=2,
            caso_tipo="licencia",
            usuario_id=10,
            plazo_objetivo=vencimiento,
            ventana_dias=3,
            usar_dias_habiles=True,
        )
    ]
    resultados = evaluar_plazos(hitos, hoy=hoy)
    assert len(resultados) == 0


def test_genera_alerta_oda_por_vencer():
    # TC-100-02: ODA con vencimiento dentro de ventana (días calendario)
    hoy = date(2026, 6, 9)
    vencimiento = hoy + timedelta(days=5)
    hitos = [
        HitoPlazos(
            tipo="oda_por_vencer",
            caso_id=3,
            caso_tipo="oda",
            usuario_id=11,
            plazo_objetivo=vencimiento,
            ventana_dias=7,
            usar_dias_habiles=False,
        )
    ]
    resultados = evaluar_plazos(hitos, hoy=hoy)
    assert len(resultados) == 1
    assert resultados[0].tipo == "oda_por_vencer"


def test_genera_alerta_consentimiento_pendiente():
    # TC-100-03: caso sin consentimiento firmado — el hito tiene plazo = hoy (urgente)
    hoy = date(2026, 6, 9)
    hitos = [
        HitoPlazos(
            tipo="consentimiento_pendiente",
            caso_id=4,
            caso_tipo="ingreso",
            usuario_id=12,
            plazo_objetivo=hoy,
            ventana_dias=30,  # siempre dentro de ventana mientras esté pendiente
            usar_dias_habiles=False,
        )
    ]
    resultados = evaluar_plazos(hitos, hoy=hoy)
    assert len(resultados) == 1
    assert resultados[0].tipo == "consentimiento_pendiente"


def test_genera_alerta_receta_por_renovar():
    # CA-5: receta con fecha de revisión en 4 días, ventana 5 → dentro
    hoy = date(2026, 6, 9)
    vencimiento = hoy + timedelta(days=4)
    hitos = [
        HitoPlazos(
            tipo="receta_por_renovar",
            caso_id=5,
            caso_tipo="ingreso",
            usuario_id=13,
            plazo_objetivo=vencimiento,
            ventana_dias=5,
            usar_dias_habiles=False,
        )
    ]
    resultados = evaluar_plazos(hitos, hoy=hoy)
    assert len(resultados) == 1


def test_genera_alerta_plazo_ept():
    # CA-3: EPT con plazo de informe dentro de ventana en días hábiles
    hoy = date(2026, 6, 9)  # martes
    plazo = date(2026, 6, 12)  # viernes, 3 días hábiles
    hitos = [
        HitoPlazos(
            tipo="plazo_ept",
            caso_id=6,
            caso_tipo="ept",
            usuario_id=14,
            plazo_objetivo=plazo,
            ventana_dias=5,
            usar_dias_habiles=True,
        )
    ]
    resultados = evaluar_plazos(hitos, hoy=hoy)
    assert len(resultados) == 1
    assert resultados[0].tipo == "plazo_ept"


def test_genera_alerta_plazo_isl():
    hoy = date(2026, 6, 9)
    plazo = hoy + timedelta(days=3)
    hitos = [
        HitoPlazos(
            tipo="plazo_isl",
            caso_id=7,
            caso_tipo="ept",
            usuario_id=14,
            plazo_objetivo=plazo,
            ventana_dias=5,
            usar_dias_habiles=False,
        )
    ]
    resultados = evaluar_plazos(hitos, hoy=hoy)
    assert len(resultados) == 1
    assert resultados[0].tipo == "plazo_isl"


def test_genera_alerta_control_medico():
    # CA-1: control médico dentro de ventana
    hoy = date(2026, 6, 9)
    plazo = hoy + timedelta(days=2)
    hitos = [
        HitoPlazos(
            tipo="control_medico",
            caso_id=8,
            caso_tipo="ingreso",
            usuario_id=15,
            plazo_objetivo=plazo,
            ventana_dias=7,
            usar_dias_habiles=False,
        )
    ]
    resultados = evaluar_plazos(hitos, hoy=hoy)
    assert len(resultados) == 1


# ---------------------------------------------------------------------------
# Idempotencia (CA-7, TC-100-05)
# ---------------------------------------------------------------------------


def test_idempotencia_excluye_alertas_ya_activas():
    # CA-7: si la misma (caso_id, tipo) ya tiene alerta activa, evaluar_plazos
    # la omite cuando se le pasa el set de claves ya existentes.
    hoy = date(2026, 6, 9)
    vencimiento = hoy + timedelta(days=2)
    hitos = [
        HitoPlazos(
            tipo="vencimiento_licencia",
            caso_id=20,
            caso_tipo="licencia",
            usuario_id=10,
            plazo_objetivo=vencimiento,
            ventana_dias=3,
            usar_dias_habiles=True,
        )
    ]
    # Primera evaluación: debe generar alerta
    primera = evaluar_plazos(hitos, hoy=hoy, alertas_activas=set())
    assert len(primera) == 1

    # Segunda evaluación con la alerta ya activa: no debe duplicar
    # DD-D: la clave incluye plazo_objetivo para que un nuevo plazo genere alerta distinta
    clave_activa = (20, "vencimiento_licencia", vencimiento)
    segunda = evaluar_plazos(hitos, hoy=hoy, alertas_activas={clave_activa})
    assert len(segunda) == 0


def test_idempotencia_nuevo_plazo_genera_nueva_alerta():
    """DD-D / RN-4: mismo caso+tipo pero con plazo_objetivo posterior → nueva alerta."""
    hoy = date(2026, 6, 9)
    vencimiento_v1 = hoy + timedelta(days=2)
    vencimiento_v2 = hoy + timedelta(days=3)  # plazo posterior (e.g. prórroga)
    hito_v2 = HitoPlazos(
        tipo="vencimiento_licencia",
        caso_id=20,
        caso_tipo="licencia",
        usuario_id=10,
        plazo_objetivo=vencimiento_v2,
        ventana_dias=5,
        usar_dias_habiles=True,
    )
    # La alerta de v1 ya existe en BD — clave con su plazo
    clave_v1 = (20, "vencimiento_licencia", vencimiento_v1)
    resultados = evaluar_plazos([hito_v2], hoy=hoy, alertas_activas={clave_v1})
    # v2 tiene plazo distinto → debe generar alerta propia
    assert len(resultados) == 1
    assert resultados[0].plazo_objetivo == vencimiento_v2


def test_evaluar_plazos_multiples_hitos_independientes():
    hoy = date(2026, 6, 9)
    hitos = [
        HitoPlazos(
            tipo="oda_por_vencer",
            caso_id=30,
            caso_tipo="oda",
            usuario_id=10,
            plazo_objetivo=hoy + timedelta(days=2),
            ventana_dias=7,
            usar_dias_habiles=False,
        ),
        HitoPlazos(
            tipo="receta_por_renovar",
            caso_id=31,
            caso_tipo="ingreso",
            usuario_id=11,
            plazo_objetivo=hoy + timedelta(days=50),  # fuera de ventana
            ventana_dias=5,
            usar_dias_habiles=False,
        ),
        HitoPlazos(
            tipo="consentimiento_pendiente",
            caso_id=32,
            caso_tipo="ingreso",
            usuario_id=12,
            plazo_objetivo=hoy,
            ventana_dias=30,
            usar_dias_habiles=False,
        ),
    ]
    resultados = evaluar_plazos(hitos, hoy=hoy)
    # Solo los hitos 0 y 2 están dentro de su ventana
    assert len(resultados) == 2
    tipos = {r.tipo for r in resultados}
    assert tipos == {"oda_por_vencer", "consentimiento_pendiente"}
