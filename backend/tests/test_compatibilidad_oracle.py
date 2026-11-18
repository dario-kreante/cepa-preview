"""Guardia de compatibilidad con Oracle para el código de `app/`.

Oracle 19c rechaza `IS 1` / `IS 0` (ORA-00908). SQLAlchemy genera esa
forma cuando se usa `.is_(True)`, `.is_(False)`, `.is_not(...)` o
`.isnot(...)` con un booleano literal. PostgreSQL lo acepta, así que el
CI obligatorio no lo detecta. Este test lo detecta con el árbol sintáctico
(`ast`), no con búsqueda de texto, para ignorar comentarios y cadenas.
"""

from __future__ import annotations

import ast
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / "app"

METODOS_PROHIBIDOS = frozenset({"is_", "is_not", "isnot"})

MENSAJE_SUGERENCIA = (
    "Usa `== true()` / `== false()` en lugar de `.is_(True)` / `.is_(False)`: "
    "Oracle rechaza `IS 1` / `IS 0` (ORA-00908)."
)


def _es_booleano_literal(nodo: ast.expr) -> bool:
    return isinstance(nodo, ast.Constant) and isinstance(nodo.value, bool)


def encontrar_is_booleano(texto_fuente: str, nombre_archivo: str = "<fragmento>") -> list[tuple[int, str]]:
    """Devuelve (línea, texto del metodo) por cada `.is_(True/False)` y variantes.

    Solo cuenta llamadas reales (`ast.Call`) cuyo argumento posicional es un
    booleano literal. Comentarios y cadenas no generan nodos Call, así que
    no se cuentan.
    """
    arbol = ast.parse(texto_fuente, filename=nombre_archivo)
    hallazgos: list[tuple[int, str]] = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        funcion = nodo.func
        if not isinstance(funcion, ast.Attribute) or funcion.attr not in METODOS_PROHIBIDOS:
            continue
        if not nodo.args or not _es_booleano_literal(nodo.args[0]):
            continue
        hallazgos.append((nodo.lineno, f".{funcion.attr}({nodo.args[0].value})"))
    return hallazgos


def _buscar_en_app(directorio: Path) -> list[str]:
    problemas: list[str] = []
    for archivo in sorted(directorio.rglob("*.py")):
        texto = archivo.read_text(encoding="utf-8")
        ruta = archivo.relative_to(directorio.parent).as_posix()
        for linea, uso in encontrar_is_booleano(texto, ruta):
            problemas.append(f"{ruta}:{linea}: {uso}")
    return problemas


def test_no_hay_is_booleano_en_app() -> None:
    problemas = _buscar_en_app(APP_DIR)
    assert not problemas, (
        "Se encontraron llamadas incompatibles con Oracle:\n  - "
        + "\n  - ".join(problemas)
        + "\n"
        + MENSAJE_SUGERENCIA
    )


def test_detector_marca_is_booleano_y_no_marca_true_funcion() -> None:
    fragmento_malo = "query = select(Oda).where(Oda.vigente.is_(True))\n"
    fragmento_bueno = "query = select(Oda).where(Oda.vigente == true())\n"

    assert encontrar_is_booleano(fragmento_malo) == [(1, ".is_(True)")]
    assert encontrar_is_booleano(fragmento_bueno) == []
