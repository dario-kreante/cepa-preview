"""usuario: permiso extra «Acceso a Auditoría» (CA-012, QA 23-11-2026)

- ``usuario.acceso_auditoria`` (Boolean, not null, default false): para un usuario Administrativo
  le da además lectura del módulo Auditoría (vista de caso, reportes y descarga Excel, log de
  auditoría). Para otros roles no tiene efecto y se guarda en false.

``server_default=sa.false()`` compila a ``false`` en Postgres y a ``0`` en Oracle (NUMBER(1)),
así las filas existentes quedan sin el permiso.

Revision ID: 1540
Revises: 1530
"""
import sqlalchemy as sa
from alembic import op

revision = "1540"
down_revision = "1530"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usuario",
        sa.Column("acceso_auditoria", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("usuario", "acceso_auditoria")
