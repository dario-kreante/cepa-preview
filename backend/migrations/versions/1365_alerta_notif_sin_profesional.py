"""alerta_notif_sin_profesional: libera las alertas abiertas asignadas por profesional_id

Hasta ahora el destinatario de una alerta (``alerta_notif.usuario_id``) se tomaba de
``Ingreso.profesional_id``, que es un id del catálogo ``profesional`` y no de ``usuario``.
Las alertas quedaban asignadas a quien tuviera ese mismo id de usuario (otra persona):
salían del panel general y, si esa persona tenía correo, el envío le llegaba a ella.

Ningún flujo asigna hoy ``usuario_id`` de otra forma (el seed de desarrollo solo asigna
tareas), así que todo ``usuario_id`` no nulo en ``alerta_notif`` viene de esa regla. Se pasan
a NULL las abiertas (pendiente / leída), que vuelven al panel general. Las resueltas se
conservan tal cual: ya no se muestran como pendientes ni se envían por correo.

El downgrade no restaura los valores: eran incorrectos y no hay de dónde recuperarlos.

Revision ID: 1365
Revises: 1360
"""

import sqlalchemy as sa
from alembic import op

revision = "1365"
down_revision = "1360"
branch_labels = None
depends_on = None

_ABIERTAS = ("pendiente", "leida")


def _liberar_alertas_abiertas() -> None:
    alerta = sa.table(
        "alerta_notif",
        sa.column("usuario_id", sa.BigInteger),
        sa.column("estado", sa.String),
    )
    op.execute(
        alerta.update()
        .where(alerta.c.usuario_id.isnot(None), alerta.c.estado.in_(_ABIERTAS))
        .values(usuario_id=None)
    )


def upgrade() -> None:
    _liberar_alertas_abiertas()


def downgrade() -> None:
    pass
