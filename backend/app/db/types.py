"""Tipos de columna portables entre motores (D15).

El tipo genérico ``sa.JSON`` de SQLAlchemy NO es portable: el dialecto Oracle de
SQLAlchemy 2.0 no implementa ``visit_JSON`` y la compilación falla
(``UnsupportedCompilationError``). ``PortableJSON`` resuelve esto delegando al
tipo JSON nativo donde existe (PostgreSQL) y serializando a texto (CLOB) en los
motores que no tienen tipo JSON nativo en el dialecto (Oracle thin).
"""

import json

from sqlalchemy import Text, TypeDecorator
from sqlalchemy.types import JSON as GenericJSON


class PortableJSON(TypeDecorator):
    """JSON portable PostgreSQL⇄Oracle.

    - PostgreSQL: usa el tipo ``JSON`` nativo (serialización a cargo del driver).
    - Otros motores (Oracle): almacena el JSON serializado en ``Text``/CLOB y
      lo (de)serializa con ``json`` en la capa de aplicación.

    Es transparente: en Postgres el comportamiento es idéntico a ``sa.JSON``.
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(GenericJSON())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if dialect.name == "postgresql" or value is None:
            return value
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if dialect.name == "postgresql" or value is None:
            return value
        return json.loads(value)
