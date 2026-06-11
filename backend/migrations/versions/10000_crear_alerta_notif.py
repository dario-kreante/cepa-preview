"""crear alerta_notif

Motor unificado de alertas por plazos perentorios (EPIC-10, CEPA-100).
La tabla se llama alerta_notif (no alerta) para coexistir con la tabla alerta
de EPIC-02 (app.models.farmacos.Alerta — alertas de revisión de recetas).

Revision ID: 10000
Revises: 09001
Create Date: 2026-06-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "10000"
down_revision = "09001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alerta_notif",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("tipo", sa.String(40), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("caso_id", sa.BigInteger(), nullable=False),
        sa.Column("caso_tipo", sa.String(30), nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("plazo_objetivo", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ventana_dias", sa.Integer(), nullable=False),
        sa.Column("generada_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resuelta_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email_enviado", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_alerta_notif_tipo", "alerta_notif", ["tipo"])
    op.create_index("ix_alerta_notif_caso_id", "alerta_notif", ["caso_id"])
    op.create_index("ix_alerta_notif_uid", "alerta_notif", ["usuario_id"])


def downgrade() -> None:
    op.drop_index("ix_alerta_notif_uid", table_name="alerta_notif")
    op.drop_index("ix_alerta_notif_caso_id", table_name="alerta_notif")
    op.drop_index("ix_alerta_notif_tipo", table_name="alerta_notif")
    op.drop_table("alerta_notif")
