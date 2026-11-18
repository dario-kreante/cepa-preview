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


NOMBRES_BOOLEANOS_SQL = frozenset({"true", "false"})
BASES_SQLALCHEMY = frozenset({"sa", "sqlalchemy"})


def _es_booleano_literal(nodo: ast.expr) -> bool:
    """`True` / `False` literales de Python."""
    return isinstance(nodo, ast.Constant) and isinstance(nodo.value, bool)


def _es_booleano_sql(nodo: ast.expr) -> bool:
    """`true()` / `false()` de SQLAlchemy, con o sin prefijo (`sa.`, `sqlalchemy.`)."""
    if not isinstance(nodo, ast.Call) or nodo.args or nodo.keywords:
        return False
    funcion = nodo.func
    if isinstance(funcion, ast.Name):
        return funcion.id in NOMBRES_BOOLEANOS_SQL
    if isinstance(funcion, ast.Attribute) and isinstance(funcion.value, ast.Name):
        return funcion.attr in NOMBRES_BOOLEANOS_SQL and funcion.value.id in BASES_SQLALCHEMY
    return False


def _es_booleano(nodo: ast.expr) -> bool:
    return _es_booleano_literal(nodo) or _es_booleano_sql(nodo)


def encontrar_is_booleano(texto_fuente: str, nombre_archivo: str = "<fragmento>") -> list[tuple[int, str]]:
    """Devuelve (línea, uso) por cada `.is_/.is_not/.isnot` con booleano.

    Booleano = literal `True`/`False`, o `true()`/`false()` de SQLAlchemy
    (también `sa.true()` y `sqlalchemy.false()`). `.is_(None)` no se marca.
    Solo cuenta llamadas reales (`ast.Call`): comentarios y cadenas no cuentan.
    """
    arbol = ast.parse(texto_fuente, filename=nombre_archivo)
    hallazgos: list[tuple[int, str]] = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        funcion = nodo.func
        if not isinstance(funcion, ast.Attribute) or funcion.attr not in METODOS_PROHIBIDOS:
            continue
        if not nodo.args or not _es_booleano(nodo.args[0]):
            continue
        hallazgos.append((nodo.lineno, f".{funcion.attr}({ast.unparse(nodo.args[0])})"))
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


CASOS_MALOS = [
    ("x.is_(True)", ".is_(True)"),
    ("x.is_(False)", ".is_(False)"),
    ("x.is_not(True)", ".is_not(True)"),
    ("x.is_not(False)", ".is_not(False)"),
    ("x.isnot(True)", ".isnot(True)"),
    ("x.isnot(False)", ".isnot(False)"),
    ("x.is_(true())", ".is_(true())"),
    ("x.is_(false())", ".is_(false())"),
    ("x.is_not(true())", ".is_not(true())"),
    ("x.isnot(false())", ".isnot(false())"),
    ("x.is_(sa.true())", ".is_(sa.true())"),
    ("x.is_not(sqlalchemy.false())", ".is_not(sqlalchemy.false())"),
    ("x.isnot(sa.false())", ".isnot(sa.false())"),
]

CASOS_BUENOS = [
    "x == true()",
    "x == false()",
    "x.is_(None)",
    "x.is_not(None)",
    "x.isnot(None)",
    "x.is_(y)",
    "sa.true()",  # sin `.is_`: no es un caso
    "# x.is_(True)  <- comentario, no cuenta",
]


def test_detector_marca_todas_las_variantes_booleanas() -> None:
    for fragmento, esperado in CASOS_MALOS:
        assert encontrar_is_booleano(fragmento + "\n") == [(1, esperado)], fragmento


def test_detector_ignora_casos_permitidos() -> None:
    for fragmento in CASOS_BUENOS:
        assert encontrar_is_booleano(fragmento + "\n") == [], fragmento
