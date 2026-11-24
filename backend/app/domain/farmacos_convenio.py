"""Clasificación de un fármaco recetado según los catálogos de convenio (QA-010 / QA-013).

Decidido el 18-11-2026: la comparación es por código SAP y por marca/presentación, y lo que
no se puede afirmar con seguridad queda en «REVISAR» para que lo mire una persona.

SIGE guarda el fármaco como texto libre (la marca de la receta o el medicamento del esquema),
sin código SAP. El orden de las reglas:

1. **Código SAP**: si el texto trae un número de 4+ dígitos (que no es una dosis) igual al
   código SAP de un fármaco de la canasta → «Convenio 002».
2. **Nombre y presentación**: el texto, separado en palabras y números, coincide por prefijo con
   la descripción de la canasta («Deprax 50 mg» ↔ «DEPRAX 50MG. CAJA 30 COMP. REC») o con la
   glosa de la lista Externalizado (truncada a 25 caracteres por el ISL, así que su última
   palabra puede venir cortada). Si todas las coincidencias son del mismo convenio → ese
   convenio; si apuntan a convenios distintos → «REVISAR».
3. **Solo la marca** coincide (otra presentación u otra dosis) → «REVISAR».
4. **Solo el principio activo** coincide → «REVISAR».
5. Nada coincide → «Fuera de convenio».
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

from app.domain.comunas import clave_texto

CONVENIO_001 = "Convenio 001"
CONVENIO_002 = "Convenio 002"
FUERA = "Fuera de convenio"
REVISAR = "REVISAR"

Clasificacion = Literal["Convenio 001", "Convenio 002", "Fuera de convenio", "REVISAR"]

# Sales y formas químicas que acompañan al principio activo y no lo identifican.
_SALES = frozenset({
    "acetato", "besilato", "bromhidrato", "calcico", "citrato", "clorhidrato", "dihidrato",
    "fumarato", "hemitartrato", "hidrobromuro", "magnesico", "maleato", "mesilato",
    "monohidrato", "oxalato", "potasico", "sodico", "succinato", "sulfato", "tartrato",
    "trihidrato",
})
# Unidades: un número seguido de una de estas es una dosis, no un código SAP.
_UNIDADES = frozenset({"mg", "mcg", "ug", "g", "gr", "ml", "ui", "comp", "cap", "caps", "x"})
_MARCAS_GENERICAS = frozenset({"generico"})
_MIN_LETRAS = 4
# El ISL corta la glosa de la prestación a 25 caracteres.
LARGO_GLOSA_ISL = 25


@dataclass(frozen=True)
class ItemCanasta:
    codigo_sap: str
    descripcion: str
    principio_activo: str | None = None
    marca: str | None = None


@dataclass(frozen=True)
class ItemExternalizado:
    glosa: str
    convenio_001: bool
    convenio_002: bool


@dataclass(frozen=True)
class Resultado:
    clasificacion: Clasificacion
    detalle: str
    codigo_sap: str | None = None
    coincidencias: tuple[str, ...] = ()


def tokens(texto: str | None) -> list[str]:
    """Palabras y números del texto, sin tildes ni mayúsculas («0,5MG.» → ["0.5", "mg"])."""
    if not texto:
        return []
    t = re.sub(r"(\d),(\d)", r"\1.\2", clave_texto(texto))
    return re.findall(r"\d+(?:\.\d+)?|[a-z]+", t)


def coincide(texto: Sequence[str], ref: Sequence[str], *, ref_truncada: bool = False) -> bool:
    """El más corto es prefijo del otro, palabra por palabra.

    Con ``ref_truncada`` (glosa del ISL cortada a 25 caracteres) la última palabra de la
    referencia puede ser el comienzo de la palabra del texto («CA» ↔ «caja», «3» ↔ «30»).
    """
    n = min(len(texto), len(ref))
    if n == 0 or not texto[0].isalpha() or len(texto[0]) < _MIN_LETRAS:
        return False
    for i in range(n):
        a, b = texto[i], ref[i]
        if a == b:
            continue
        ultima_ref = i == n - 1 and len(ref) == n
        if ref_truncada and ultima_ref and a.startswith(b):
            continue
        return False
    return True


class Clasificador:
    """Arma los índices una vez y clasifica muchos textos."""

    def __init__(self, canasta: Iterable[ItemCanasta], externalizado: Iterable[ItemExternalizado]):
        self.canasta = [(c, tokens(c.descripcion)) for c in canasta]
        self.externalizado = [(e, tokens(e.glosa)) for e in externalizado]
        self.por_sap = {c.codigo_sap.strip().lstrip("0"): c for c, _ in self.canasta}

        self.principios: dict[str, str] = {}
        for c, _ in self.canasta:
            for tok in tokens(c.principio_activo):
                if tok.isalpha() and len(tok) >= 5 and tok not in _SALES:
                    self.principios.setdefault(tok, c.principio_activo or tok)

        self.marcas: dict[str, str] = {}
        for c, toks in self.canasta:
            marca = tokens(c.marca)
            if not marca or marca[0] in _MARCAS_GENERICAS:
                continue
            for tok in (marca[0], toks[0] if toks else ""):
                if tok.isalpha() and len(tok) >= _MIN_LETRAS and tok not in self.principios:
                    self.marcas.setdefault(tok, c.marca or tok)
        for e, toks in self.externalizado:
            if toks and toks[0].isalpha() and len(toks[0]) >= _MIN_LETRAS and toks[0] not in self.principios:
                self.marcas.setdefault(toks[0], toks[0].upper())

    def _por_sap(self, toks: list[str]) -> ItemCanasta | None:
        for i, tok in enumerate(toks):
            if not tok.isdigit() or len(tok) < 4:
                continue
            siguiente = toks[i + 1] if i + 1 < len(toks) else None
            if siguiente in _UNIDADES:
                continue
            item = self.por_sap.get(tok.lstrip("0"))
            if item is not None:
                return item
        return None

    def clasificar(self, texto: str | None) -> Resultado:
        toks = tokens(texto)
        if not toks:
            return Resultado(REVISAR, "Sin nombre de fármaco.")

        item = self._por_sap(toks)
        if item is not None:
            return Resultado(
                CONVENIO_002, f"Código SAP {item.codigo_sap} en la canasta del Convenio 002.",
                item.codigo_sap, (item.descripcion,),
            )

        en_canasta = [c for c, ref in self.canasta if coincide(toks, ref)]
        en_lista = [
            e for e, ref in self.externalizado
            if coincide(toks, ref, ref_truncada=len(e.glosa) >= LARGO_GLOSA_ISL)
        ]
        convenios: set[str] = set()
        if en_canasta:
            convenios.add(CONVENIO_002)
        for e in en_lista:
            if e.convenio_001:
                convenios.add(CONVENIO_001)
            if e.convenio_002:
                convenios.add(CONVENIO_002)
        coincidencias = tuple(
            dict.fromkeys([c.descripcion for c in en_canasta] + [e.glosa for e in en_lista])
        )
        if len(convenios) > 1:
            return Resultado(
                REVISAR, "Coincide con opciones de distintos convenios (" + " y ".join(sorted(convenios)) + ").",
                None, coincidencias,
            )
        if len(convenios) == 1:
            convenio = convenios.pop()
            sap = en_canasta[0].codigo_sap if len({c.codigo_sap for c in en_canasta}) == 1 else None
            fuente = []
            if en_canasta:
                fuente.append("la canasta del Convenio 002")
            if en_lista:
                fuente.append("la lista Externalizado")
            return Resultado(convenio, "Coincide con " + " y ".join(fuente) + ".", sap, coincidencias)

        marca = next((self.marcas[t] for t in toks if t in self.marcas), None)
        if marca is not None:
            parecidos = tuple(
                c.descripcion for c, ref in self.canasta if ref and ref[0] == toks[0]
            ) + tuple(e.glosa for e, ref in self.externalizado if ref and ref[0] == toks[0])
            return Resultado(
                REVISAR, f"La marca {marca} está en convenio, pero no esta presentación o dosis.",
                None, parecidos,
            )

        principio = next((self.principios[t] for t in toks if t in self.principios), None)
        if principio is not None:
            return Resultado(
                REVISAR, f"Solo coincide el principio activo ({principio}).", None, ()
            )
        return Resultado(FUERA, "No está en la canasta del Convenio 002 ni en la lista Externalizado.")
