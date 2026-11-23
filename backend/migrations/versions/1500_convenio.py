"""convenio: catálogo de convenios espejo de SALUTEM y ``ingreso.tipo_convenio`` de 120

- Crea la tabla ``convenio`` (nombre, nombre normalizado único, ``salutem_id`` único,
  ``activo_salutem``, ``visible``, ``sincronizado_en``). La llena el sync de SALUTEM y se
  completa a mano desde Configuración.
- Amplía ``ingreso.tipo_convenio`` de 40 a 120: hay convenios de SALUTEM con nombres más largos.

El downgrade borra la tabla y vuelve la columna a 40, truncando antes los valores más largos.

Revision ID: 1500
Revises: 1490
"""
import sqlalchemy as sa
from alembic import op

revision = "1500"
down_revision = "1490"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "convenio",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("nombre_normalizado", sa.String(120), nullable=False),
        sa.Column("salutem_id", sa.BigInteger(), nullable=True),
        sa.Column("activo_salutem", sa.Boolean(), nullable=False),
        sa.Column("visible", sa.Boolean(), nullable=False),
        sa.Column("sincronizado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("nombre_normalizado", name="uq_convenio_nombre_norm"),
        sa.UniqueConstraint("salutem_id", name="uq_convenio_salutem_id"),
    )
    op.alter_column(
        "ingreso", "tipo_convenio", type_=sa.String(120), existing_type=sa.String(40), existing_nullable=True
    )


def downgrade() -> None:
    op.execute("UPDATE ingreso SET tipo_convenio = SUBSTR(tipo_convenio, 1, 40) WHERE LENGTH(tipo_convenio) > 40")
    op.alter_column(
        "ingreso", "tipo_convenio", type_=sa.String(40), existing_type=sa.String(120), existing_nullable=True
    )
    op.drop_table("convenio")
