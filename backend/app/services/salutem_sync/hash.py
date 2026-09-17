"""Hash canónico del contenido que devuelve SALUTEM.

Dos respuestas con los mismos datos deben dar el mismo hash aunque cambie el
orden de las claves. Si la validación en QA muestra campos que cambian entre
consultas sin un cambio real, se agregan a CAMPOS_VOLATILES.
"""

import hashlib
import json
from typing import Any

CAMPOS_VOLATILES: frozenset[str] = frozenset()


def hash_contenido(contenido: dict[str, Any]) -> str:
    limpio = {k: v for k, v in contenido.items() if k not in CAMPOS_VOLATILES}
    canonico = json.dumps(
        limpio, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str
    )
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()
