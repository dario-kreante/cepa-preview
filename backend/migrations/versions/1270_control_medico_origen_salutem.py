"""control_medico: origen (CEPA/SALUTEM) y salutem_cita_id para los controles del sync

Revision ID: 1270
Revises: 1260
"""

import sqlalchemy as sa
from alembic import op

revision = "1270"
down_revision = "1260"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "control_medico",
        sa.Column("origen", sa.String(length=20), nullable=False, server_default="CEPA"),
    )
    op.add_column("control_medico", sa.Column("salutem_cita_id", sa.BigInteger(), nullable=True))
    op.create_index("ix_ctrl_med_sal_cita", "control_medico", ["salutem_cita_id"])


def downgrade() -> None:
    op.drop_index("ix_ctrl_med_sal_cita", table_name="control_medico")
    op.drop_column("control_medico", "salutem_cita_id")
    op.drop_column("control_medico", "origen")
