"""SPIKE SSO UTalca: agregar usuario.rut

El SSO institucional (huemul.utalca.cl) identifica a la persona por RUT, así que
hace falta un puente entre esa identidad y el usuario del CEPA.

Nullable: los usuarios locales que entran con contraseña no tienen RUT asociado.
Único: un RUT corresponde a una sola persona, y el login SSO lo usa como clave
de búsqueda — permitir duplicados haría ambiguo a quién se autentica.

Revision ID: 1230
Revises: 1221
"""

import sqlalchemy as sa
from alembic import op

revision = "1230"
down_revision = "1221"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("usuario", sa.Column("rut", sa.String(length=12), nullable=True))
    op.create_unique_constraint("uq_usuario_rut", "usuario", ["rut"])


def downgrade() -> None:
    op.drop_constraint("uq_usuario_rut", "usuario", type_="unique")
    op.drop_column("usuario", "rut")
