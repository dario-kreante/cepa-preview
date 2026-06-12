"""Validador de parametrización de formularios (CEPA-111).

Recibe una lista de dicts con los atributos de FieldDef (o instancias ORM convertidas
a dict) y devuelve una lista de errores. Lista vacía = formulario bien parametrizado.

Reglas implementadas (CEPA-111 RN-1 a RN-4):
- Todos los campos obligatorios del sistema deben estar presentes, activos y system_locked.
- Ningún campo system_locked puede estar inactive.
- Cada campo debe tener field_type en el conjunto válido y label no vacío.
- Campos de tipo 'select' marcados required deben tener domain_values no vacío.
- No puede haber field_key duplicado.
"""

from __future__ import annotations

# Identificadores normalizados de los 7 campos obligatorios del sistema (D6 / CEPA-111 RN-2).
SYSTEM_REQUIRED_FIELDS: tuple[str, ...] = (
    "sexo",
    "edad",
    "diagnostico",
    "modelo_trat",
    "tipo_alta",
    "tipo_ingreso",
    "tipo_convenio",
)

VALID_FIELD_TYPES: frozenset[str] = frozenset({"text", "number", "date", "select", "boolean"})


class ParametrizationError(Exception):
    """Se lanza cuando validate_form_version detecta errores y el llamador decide abortar."""

    def __init__(self, errors: list[dict[str, str]]) -> None:
        self.errors = errors
        super().__init__(f"Formulario mal parametrizado: {len(errors)} error(es)")


def validate_form_version(fields: list[dict]) -> list[dict[str, str]]:
    """Valida la lista de definiciones de campo de una versión de formulario.

    Cada elemento de `fields` debe contener al menos las claves:
        field_key, field_type, required, system_locked, domain_values, active, label.

    Retorna lista de dicts {"field_key": ..., "error": ...}.
    Lista vacía indica formulario bien parametrizado y listo para publicar.
    """
    errors: list[dict[str, str]] = []

    # 1. Detectar field_key duplicados
    seen_keys: set[str] = set()
    for f in fields:
        key = f.get("field_key", "")
        if key in seen_keys:
            errors.append(
                {"field_key": key, "error": f"field_key duplicado: '{key}'"}
            )
        seen_keys.add(key)

    # Índice para búsquedas posteriores (usamos el primero con ese key)
    index: dict[str, dict] = {}
    for f in fields:
        k = f.get("field_key", "")
        if k not in index:
            index[k] = f

    # 2. Campos obligatorios del sistema deben estar presentes, activos y system_locked
    for required_key in SYSTEM_REQUIRED_FIELDS:
        if required_key not in index:
            errors.append(
                {
                    "field_key": required_key,
                    "error": (
                        f"Campo obligatorio del sistema '{required_key}' ausente en el formulario."
                    ),
                }
            )
            continue
        f = index[required_key]
        if not f.get("active", True):
            errors.append(
                {
                    "field_key": required_key,
                    "error": (
                        f"Campo system_locked '{required_key}' no puede estar inactivo."
                    ),
                }
            )
        if not f.get("system_locked", False):
            errors.append(
                {
                    "field_key": required_key,
                    "error": (
                        f"Campo obligatorio del sistema '{required_key}' debe tener "
                        "system_locked=True."
                    ),
                }
            )

    # 3. Validar cada campo individualmente
    for f in fields:
        key = f.get("field_key", "(sin clave)")

        # 3a. Etiqueta no vacía
        label = (f.get("label") or "").strip()
        if not label:
            errors.append(
                {"field_key": key, "error": f"Campo '{key}' sin etiqueta (label vacío)."}
            )

        # 3b. field_type en conjunto válido (None y "" se tratan como ausente — D15/Oracle)
        ftype = (f.get("field_type") or "").strip()
        if not ftype:
            errors.append(
                {"field_key": key, "error": f"Campo '{key}' sin tipo de dato (field_type vacío)."}
            )
        elif ftype not in VALID_FIELD_TYPES:
            errors.append(
                {
                    "field_key": key,
                    "error": (
                        f"Campo '{key}' tiene field_type inválido: '{ftype}'. "
                        f"Valores válidos: {sorted(VALID_FIELD_TYPES)}."
                    ),
                }
            )

        # 3c. Select obligatorio debe tener domain_values
        if ftype == "select" and f.get("required", False):
            dv = f.get("domain_values")
            if not dv:
                errors.append(
                    {
                        "field_key": key,
                        "error": (
                            f"Campo select obligatorio '{key}' sin domain_values definido."
                        ),
                    }
                )

    return errors
