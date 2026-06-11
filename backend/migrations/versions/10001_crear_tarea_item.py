"""crear tarea_item

Tareas operativas por rol (EPIC-10, CEPA-103).

Revision ID: 10001
Revises: 10000
Create Date: 2026-06-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "10001"
down_revision = "10000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tarea_item",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("titulo", sa.String(120), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("tipo_tarea", sa.String(60), nullable=False),
        sa.Column("caso_id", sa.BigInteger(), nullable=True),
        sa.Column("caso_tipo", sa.String(30), nullable=True),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("creada_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completada_por", sa.String(120), nullable=True),
    )
    op.create_index("ix_tarea_item_usuario_id", "tarea_item", ["usuario_id"])


def downgrade() -> None:
    op.drop_index("ix_tarea_item_usuario_id", table_name="tarea_item")
    op.drop_table("tarea_item")
