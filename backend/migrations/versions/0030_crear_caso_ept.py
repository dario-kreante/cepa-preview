"""crear caso_ept contacto_ept proceso_ept plazo_ept

Revision ID: 0030
Revises: 0024
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0030"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "caso_ept",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("ingreso_id", sa.BigInteger(), nullable=False),
        sa.Column("mes", sa.String(length=20), nullable=False),
        sa.Column("fecha_ingreso_ept", sa.Date(), nullable=False),
        sa.Column("nombre_trabajador", sa.String(length=160), nullable=False),
        sa.Column("rut_trabajador", sa.String(length=12), nullable=False),
        sa.Column("region_trabajador", sa.String(length=80), nullable=False),
        sa.Column("eista", sa.String(length=160), nullable=False),
        sa.Column("factor_riesgo", sa.String(length=40), nullable=False),
        sa.Column("corresponde_ept", sa.Boolean(), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("razon_social", sa.String(length=160), nullable=True),
        sa.Column("unidad_cargo_horario", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ingreso_id"], ["ingreso.id"], name="fk_caso_ept_ingreso"
        ),
    )
    op.create_index("ix_caso_ept_ingreso_id", "caso_ept", ["ingreso_id"])
    op.create_index("ix_caso_ept_rut_trab", "caso_ept", ["rut_trabajador"])

    op.create_table(
        "contacto_ept",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("caso_ept_id", sa.BigInteger(), nullable=False),
        sa.Column("correo", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["caso_ept_id"], ["caso_ept.id"], name="fk_contacto_ept_caso"
        ),
    )
    op.create_index("ix_contacto_ept_caso_id", "contacto_ept", ["caso_ept_id"])

    op.create_table(
        "proceso_ept",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("caso_ept_id", sa.BigInteger(), nullable=False),
        sa.Column("plazo_evid_denunciante", sa.Date(), nullable=True),
        sa.Column("plazo_insumos_empresa", sa.Date(), nullable=True),
        sa.Column("hay_testigos", sa.Boolean(), nullable=False),
        sa.Column("testigos_cantidad", sa.Integer(), nullable=False),
        sa.Column("num_entrevistas", sa.Integer(), nullable=False),
        sa.Column("insumos_eista", sa.Text(), nullable=True),
        sa.Column("doc_incumplimiento", sa.Text(), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["caso_ept_id"], ["caso_ept.id"], name="fk_proceso_ept_caso"
        ),
    )
    op.create_unique_constraint("uq_proceso_ept_caso", "proceso_ept", ["caso_ept_id"])

    op.create_table(
        "plazo_ept",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("caso_ept_id", sa.BigInteger(), nullable=False),
        sa.Column("plazo_informe_ept", sa.Date(), nullable=True),
        sa.Column("plazo_portal_isl", sa.Date(), nullable=True),
        sa.Column("fecha_entrega_isl", sa.Date(), nullable=True),
        sa.Column("fecha_envio", sa.Date(), nullable=True),
        sa.Column("estado_informe", sa.String(length=20), nullable=False),
        sa.Column("estado_entrega_isl", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["caso_ept_id"], ["caso_ept.id"], name="fk_plazo_ept_caso"
        ),
    )
    op.create_unique_constraint("uq_plazo_ept_caso", "plazo_ept", ["caso_ept_id"])


def downgrade() -> None:
    op.drop_constraint("uq_plazo_ept_caso", "plazo_ept", type_="unique")
    op.drop_table("plazo_ept")

    op.drop_constraint("uq_proceso_ept_caso", "proceso_ept", type_="unique")
    op.drop_table("proceso_ept")

    op.drop_index("ix_contacto_ept_caso_id", table_name="contacto_ept")
    op.drop_table("contacto_ept")

    op.drop_index("ix_caso_ept_rut_trab", table_name="caso_ept")
    op.drop_index("ix_caso_ept_ingreso_id", table_name="caso_ept")
    op.drop_table("caso_ept")
