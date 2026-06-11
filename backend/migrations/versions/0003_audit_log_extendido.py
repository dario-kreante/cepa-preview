"""audit_log extendido + inmutable

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-10 00:20:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_log", sa.Column("rol", sa.String(length=20), nullable=True))
    op.add_column("audit_log", sa.Column("valor_anterior", sa.Text(), nullable=True))
    op.add_column("audit_log", sa.Column("valor_nuevo", sa.Text(), nullable=True))

    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION audit_log_inmutable()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'audit_log es inmutable: no se permite % ', TG_OP;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_audit_log_inmutable
            BEFORE UPDATE OR DELETE ON audit_log
            FOR EACH ROW EXECUTE FUNCTION audit_log_inmutable();
            """
        )
    elif dialect == "oracle":
        op.execute(
            """
            CREATE OR REPLACE TRIGGER trg_audit_log_inmutable
            BEFORE UPDATE OR DELETE ON audit_log
            FOR EACH ROW
            BEGIN
                RAISE_APPLICATION_ERROR(-20001, 'audit_log es inmutable');
            END;
            """
        )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_audit_log_inmutable ON audit_log;")
        op.execute("DROP FUNCTION IF EXISTS audit_log_inmutable();")
    elif dialect == "oracle":
        op.execute("DROP TRIGGER trg_audit_log_inmutable")

    op.drop_column("audit_log", "valor_nuevo")
    op.drop_column("audit_log", "valor_anterior")
    op.drop_column("audit_log", "rol")
