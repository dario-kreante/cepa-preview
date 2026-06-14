"""crear consentimiento

Revision ID: 0015
Revises: 0014
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "consentimiento",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("ingreso_id", sa.BigInteger(), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("evidencia_ref", sa.String(length=255), nullable=True),
        sa.Column("fecha_firma", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ingreso_id"], ["ingreso.id"], name="fk_consent_ingreso"),
    )
    op.create_unique_constraint("uq_consent_ingreso", "consentimiento", ["ingreso_id"])


def downgrade() -> None:
    op.drop_constraint("uq_consent_ingreso", "consentimiento", type_="unique")
    op.drop_table("consentimiento")
