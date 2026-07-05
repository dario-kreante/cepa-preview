
from app.services.form_validator import (
    SYSTEM_REQUIRED_FIELDS,
    validate_form_version,
)


def _field(
    field_key: str,
    field_type: str = "text",
    required: bool = True,
    system_locked: bool = False,
    domain_values: list | None = None,
    active: bool = True,
    label: str = "Etiqueta",
):
    """Helper: devuelve un dict que imita los atributos de un FieldDef."""
    return {
        "field_key": field_key,
        "field_type": field_type,
        "required": required,
        "system_locked": system_locked,
        "domain_values": domain_values,
        "active": active,
        "label": label,
    }


def _all_system_fields():
    """Genera la lista mínima de campos obligatorios del sistema bien parametrizados."""
    tipo_select = {
        "tipo_alta": ["terapeutica", "medica", "psicologica", "abandono", "derivacion"],
        "tipo_ingreso": ["consulta_espontanea", "convenio", "proyecto", "particular"],
        "tipo_convenio": ["ISL", "SUSESO", "particular", "otro"],
    }
    fields = []
    for key in SYSTEM_REQUIRED_FIELDS:
        ftype = "select" if key in tipo_select else "text"
        dv = tipo_select.get(key)
        fields.append(
            _field(
                field_key=key,
                field_type=ftype,
                required=True,
                system_locked=True,
                domain_values=dv,
                active=True,
            )
        )
    return fields


# TC-111-01: formulario con los 7 campos obligatorios bien parametrizados → sin errores
def test_formulario_valido_sin_errores():
    campos = _all_system_fields()
    errores = validate_form_version(campos)
    assert errores == [], f"Se esperaba lista vacía, obtuvo: {errores}"


# TC-111-02: campo sin tipo de dato → error de parametrización
def test_campo_sin_tipo_bloquea_publicacion():
    campos = _all_system_fields()
    campos.append(_field("extra", field_type=""))
    errores = validate_form_version(campos)
    assert any("field_type" in e["error"] or "tipo" in e["error"].lower() for e in errores)


# TC-111-02: campo sin etiqueta → error
def test_campo_sin_label_bloquea_publicacion():
    campos = _all_system_fields()
    campos.append(_field("extra2", label=""))
    errores = validate_form_version(campos)
    assert any("label" in e["error"].lower() or "etiqueta" in e["error"].lower() for e in errores)


# TC-111-03: formulario sin campo obligatorio del sistema → error
def test_campo_obligatorio_sistema_faltante_bloquea():
    campos = [f for f in _all_system_fields() if f["field_key"] != "diagnostico"]
    errores = validate_form_version(campos)
    assert any("diagnostico" in e["error"] for e in errores)


# TC-111-03: campo system_locked no puede marcarse inactive
def test_campo_system_locked_no_puede_desactivarse():
    campos = _all_system_fields()
    for c in campos:
        if c["field_key"] == "sexo":
            c["active"] = False
    errores = validate_form_version(campos)
    assert any("sexo" in e["error"] and "system_locked" in e["error"] for e in errores)


# TC-111-05: campo select obligatorio sin domain_values → error
def test_campo_select_obligatorio_sin_dominio_da_error():
    campos = _all_system_fields()
    for c in campos:
        if c["field_key"] == "tipo_ingreso":
            c["domain_values"] = None
    errores = validate_form_version(campos)
    assert any("tipo_ingreso" in e["error"] for e in errores)


# RN-1: campo con field_key duplicado → error
def test_field_key_duplicado_es_error():
    campos = _all_system_fields()
    campos.append(_field("sexo", field_type="text"))  # duplicado
    errores = validate_form_version(campos)
    assert any("duplicado" in e["error"].lower() or "duplicated" in e["error"].lower() for e in errores)


# RN-1: field_type fuera del conjunto válido → error
def test_field_type_invalido_es_error():
    campos = _all_system_fields()
    campos.append(_field("nuevo_campo", field_type="imagen"))
    errores = validate_form_version(campos)
    assert any("field_type" in e["error"] or "tipo" in e["error"].lower() for e in errores)


# TC-CEPA-111-001: field_key de campo custom con nomenclatura no estándar → error
def test_field_key_custom_con_nomenclatura_no_estandar_bloquea_publicacion():
    campos = _all_system_fields()
    campos.append(_field("campoX1", field_type="text"))
    errores = validate_form_version(campos)
    assert any("campoX1" in e["error"] for e in errores)


# Nomenclatura estándar: guiones, espacios o mayúsculas también deben rechazarse
def test_field_key_custom_con_guion_o_espacio_bloquea_publicacion():
    campos = _all_system_fields()
    campos.append(_field("campo-nuevo", field_type="text"))
    campos.append(_field("campo nuevo", field_type="text"))
    errores = validate_form_version(campos)
    assert any("campo-nuevo" in e["error"] for e in errores)
    assert any("campo nuevo" in e["error"] for e in errores)


# Nomenclatura estándar: snake_case válido (minúsculas, números, guion bajo) no genera error
def test_field_key_custom_snake_case_valido_no_da_error():
    campos = _all_system_fields()
    campos.append(_field("campo_extra_2", field_type="text"))
    errores = validate_form_version(campos)
    assert not any("campo_extra_2" in e["error"] for e in errores)
