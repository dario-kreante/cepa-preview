"""Corrección DD-3: eliminar columnas de dimensión duplicadas de ingreso.

Las columnas sexo, region, comuna, tramo_etario se agregaron en 09000 pero
duplican datos que ya viven en la tabla paciente. Los filtros del dashboard
y reportes ahora hacen JOIN a paciente en lugar de leer ingreso.sexo/etc.
La columna tramo_etario se deriva de paciente.edad en tiempo de consulta.

Chained on head 10001.

Revision ID: 11000
Revises: 10001
Create Date: 2026-06-11 00:00:00.000000
"""
from alembic import op

revision = "11000"
down_revision = "10001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ingreso") as batch_op:
        batch_op.drop_column("sexo")
        batch_op.drop_column("region")
        batch_op.drop_column("comuna")
        batch_op.drop_column("tramo_etario")


def downgrade() -> None:
    import sqlalchemy as sa

    with op.batch_alter_table("ingreso") as batch_op:
        batch_op.add_column(sa.Column("tramo_etario", sa.String(20), nullable=True))
        batch_op.add_column(sa.Column("comuna", sa.String(80), nullable=True))
        batch_op.add_column(sa.Column("region", sa.String(80), nullable=True))
        batch_op.add_column(sa.Column("sexo", sa.String(10), nullable=True))
