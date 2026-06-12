"""crear form_definition form_version field_def

Revision ID: 11002
Revises: 11001
Create Date: 2026-06-11 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "11002"
down_revision = "11001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "form_definition",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("form_key", sa.String(length=60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_unique_constraint("uq_formdef_key", "form_definition", ["form_key"])

    op.create_table(
        "form_version",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("form_def_id", sa.BigInteger(), nullable=False),
        sa.Column("version_num", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["form_def_id"], ["form_definition.id"], name="fk_formver_formdef"
        ),
        sa.UniqueConstraint("form_def_id", "version_num", name="uq_formver_def_num"),
    )
    op.create_index("ix_form_version_def_id", "form_version", ["form_def_id"])

    op.create_table(
        "field_def",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("form_version_id", sa.BigInteger(), nullable=False),
        sa.Column("field_key", sa.String(length=60), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("field_type", sa.String(length=20), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("system_locked", sa.Boolean(), nullable=False),
        sa.Column("domain_values", sa.JSON(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["form_version_id"], ["form_version.id"], name="fk_fielddef_formver"
        ),
    )
    op.create_index("ix_field_def_ver_id", "field_def", ["form_version_id"])


def downgrade() -> None:
    op.drop_index("ix_field_def_ver_id", table_name="field_def")
    op.drop_table("field_def")
    op.drop_index("ix_form_version_def_id", table_name="form_version")
    op.drop_table("form_version")
    op.drop_constraint("uq_formdef_key", "form_definition", type_="unique")
    op.drop_table("form_definition")
