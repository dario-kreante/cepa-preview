import pytest
from pydantic import ValidationError

from app.schemas.farmacos import (
    EsquemaIndicacionCreate,
    RecetaCreate,
    RegistroFarmacologicoCreate,
    SeguimTratamientoCreate,
)


# ── RegistroFarmacologicoCreate ──────────────────────────────────────────────

def test_reg_farm_requiere_ingreso_id_medico_y_estado():
    with pytest.raises(ValidationError) as exc:
        RegistroFarmacologicoCreate(medico_tratante="Dr. X", estado_farmacologico="activo")
    errors = {e["loc"][0] for e in exc.value.errors()}
    assert "ingreso_id" in errors


def test_reg_farm_estado_invalido_rechazado():
    with pytest.raises(ValidationError):
        RegistroFarmacologicoCreate(
            ingreso_id=1,
            medico_tratante="Dr. X",
            estado_farmacologico="inventado",
        )


def test_reg_farm_valido():
    obj = RegistroFarmacologicoCreate(
        ingreso_id=1,
        medico_tratante="Dr. González",
        estado_farmacologico="activo",
    )
    assert obj.ingreso_id == 1
    assert obj.estado_farmacologico == "activo"


# ── EsquemaIndicacionCreate ──────────────────────────────────────────────────

def test_indicacion_requiere_medicamento_dosis_frecuencia():
    with pytest.raises(ValidationError) as exc:
        EsquemaIndicacionCreate(registro_id=1, medicamento="Sertralina")
    errors = {e["loc"][0] for e in exc.value.errors()}
    assert "dosis" in errors
    assert "frecuencia" in errors


def test_indicacion_frecuencia_invalida_rechazada():
    with pytest.raises(ValidationError):
        EsquemaIndicacionCreate(
            registro_id=1,
            medicamento="Sertralina",
            dosis="50 mg",
            frecuencia="cada luna llena",
        )


def test_indicacion_extra_sistema_por_defecto_false():
    obj = EsquemaIndicacionCreate(
        registro_id=1,
        medicamento="Sertralina",
        dosis="50 mg",
        frecuencia="c/24h",
    )
    assert obj.extra_sistema is False


def test_indicacion_extra_sistema_true():
    obj = EsquemaIndicacionCreate(
        registro_id=1,
        medicamento="MedicamentoExtranjero X",
        dosis="10 mg",
        frecuencia="c/12h",
        extra_sistema=True,
    )
    assert obj.extra_sistema is True


# ── RecetaCreate ─────────────────────────────────────────────────────────────

def test_receta_revision_no_puede_ser_anterior_a_emision():
    """CEPA-022 RN-5: fecha_revision no puede ser anterior a fecha_emision."""
    with pytest.raises(ValidationError) as exc:
        RecetaCreate(
            registro_id=1,
            fecha_emision="2026-06-10",
            fecha_revision="2026-06-05",
            marca_medicamento="Fluoxetina",
        )
    errores = str(exc.value)
    assert "revision" in errores.lower() or "emision" in errores.lower()


def test_receta_envio_no_puede_ser_anterior_a_emision():
    """CEPA-022 RN-5: fecha_envio no puede ser anterior a fecha_emision."""
    with pytest.raises(ValidationError) as exc:
        RecetaCreate(
            registro_id=1,
            fecha_emision="2026-06-10",
            fecha_revision="2026-06-20",
            fecha_envio="2026-06-09",
            marca_medicamento="Fluoxetina",
        )
    errores = str(exc.value)
    assert "envio" in errores.lower() or "emision" in errores.lower()


def test_receta_valida():
    obj = RecetaCreate(
        registro_id=1,
        fecha_emision="2026-06-01",
        fecha_revision="2026-06-20",
        fecha_envio="2026-06-05",
        marca_medicamento="Fluoxetina genérico",
    )
    assert obj.marca_medicamento == "Fluoxetina genérico"


# ── SeguimTratamientoCreate ──────────────────────────────────────────────────

def test_seguim_disminucion_true_requiere_plan():
    """CEPA-023 RN-1: plan obligatorio si disminucion_farmacos=True."""
    with pytest.raises(ValidationError) as exc:
        SeguimTratamientoCreate(
            registro_id=1,
            disminucion_farmacos=True,
            cambio_esquema=False,
        )
    errores = str(exc.value)
    assert "plan_disminucion" in errores


def test_seguim_cambio_true_requiere_detalle():
    """CEPA-023 RN-2: detalle obligatorio si cambio_esquema=True."""
    with pytest.raises(ValidationError) as exc:
        SeguimTratamientoCreate(
            registro_id=1,
            disminucion_farmacos=False,
            cambio_esquema=True,
        )
    errores = str(exc.value)
    assert "detalle_cambio" in errores


def test_seguim_ambos_false_sin_detalles_valido():
    obj = SeguimTratamientoCreate(
        registro_id=1,
        disminucion_farmacos=False,
        cambio_esquema=False,
        observaciones="Sin cambios esta semana.",
    )
    assert obj.observaciones == "Sin cambios esta semana."
    assert obj.plan_disminucion is None
    assert obj.detalle_cambio is None


def test_seguim_disminucion_true_con_plan_valido():
    obj = SeguimTratamientoCreate(
        registro_id=1,
        disminucion_farmacos=True,
        plan_disminucion="Reducir 25 mg/semana.",
        cambio_esquema=False,
    )
    assert obj.plan_disminucion == "Reducir 25 mg/semana."


def test_seguim_cambio_true_con_detalle_valido():
    obj = SeguimTratamientoCreate(
        registro_id=1,
        disminucion_farmacos=False,
        cambio_esquema=True,
        detalle_cambio="Agregar Clonazepam 0.5 mg c/24h.",
    )
    assert obj.detalle_cambio == "Agregar Clonazepam 0.5 mg c/24h."
