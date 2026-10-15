"""salutem_archivo: metadata de la biblioteca de archivos de SALUTEM

Solo id, nombre, tipo y fecha de cada archivo; el contenido se pide a SALUTEM al abrirlo.

Revision ID: 1320
Revises: 1310
"""

import sqlalchemy as sa
from alembic import op

revision = "1320"
down_revision = "1310"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "salutem_archivo",
        sa.Column("archivo_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("persona_id", sa.BigInteger(), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("tipo", sa.String(length=30), nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=True),
        sa.Column("visto_ultima_vez", sa.DateTime(timezone=True), nullable=False),
        sa.Column("desaparecido_en", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("archivo_id"),
    )
    op.create_index("ix_salutem_archivo_persona_id", "salutem_archivo", ["persona_id"])
    op.create_index("ix_salutem_archivo_fecha", "salutem_archivo", ["fecha_creacion"])


def downgrade() -> None:
    op.drop_index("ix_salutem_archivo_fecha", table_name="salutem_archivo")
    op.drop_index("ix_salutem_archivo_persona_id", table_name="salutem_archivo")
    op.drop_table("salutem_archivo")
