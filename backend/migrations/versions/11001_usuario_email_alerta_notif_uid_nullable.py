"""DD-C / DD-A: agregar usuario.email y hacer alerta_notif.usuario_id nullable.

- usuario.email String(160) nullable: correo de contacto para notificaciones
  de alerta (CEPA-102, DD-C).
- alerta_notif.usuario_id: cambia de NOT NULL a NULL para soportar alertas
  globales de Coordinación cuando el ingreso no tiene profesional_id (DD-A / PA).

Chained on head 11000.

Revision ID: 11001
Revises: 11000
Create Date: 2026-06-11 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "11001"
down_revision = "11000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # DD-C: correo en usuario
    with op.batch_alter_table("usuario") as batch_op:
        batch_op.add_column(sa.Column("email", sa.String(160), nullable=True))

    # DD-A / PA: usuario_id nullable en alerta_notif
    with op.batch_alter_table("alerta_notif") as batch_op:
        batch_op.alter_column(
            "usuario_id",
            existing_type=sa.BigInteger(),
            nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("alerta_notif") as batch_op:
        # Revertir a NOT NULL (requiere que no haya NULLs en la columna)
        batch_op.alter_column(
            "usuario_id",
            existing_type=sa.BigInteger(),
            nullable=False,
        )

    with op.batch_alter_table("usuario") as batch_op:
        batch_op.drop_column("email")
