"""paciente.salutem_persona_id: cruce con SALUTEM para personas sin RUT

Revision ID: 1260
Revises: 1250
"""

import sqlalchemy as sa
from alembic import op

revision = "1260"
down_revision = "1250"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("paciente", sa.Column("salutem_persona_id", sa.BigInteger(), nullable=True))
    op.create_unique_constraint("uq_paciente_salutem_persona", "paciente", ["salutem_persona_id"])


def downgrade() -> None:
    op.drop_constraint("uq_paciente_salutem_persona", "paciente", type_="unique")
    op.drop_column("paciente", "salutem_persona_id")
