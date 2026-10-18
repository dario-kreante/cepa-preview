"""profesional: datos que entrega SALUTEM y vínculo con controles y fichas

- ``profesional``: id de SALUTEM (único, nulo para los cargados a mano), especialidades y
  sucursales (listas JSON de nombres), primera/última atención y última sincronización.
- ``control_medico`` y ``ficha_clinica``: ``profesional_id`` (FK nullable al catálogo). Lo
  llena el sync desde ``profesionalId`` y, en controles manuales, el selector del catálogo.
- Nombres de índices y constraints de máximo 30 caracteres (Oracle 19c). La UNIQUE sobre una
  columna nullable admite varias filas sin id en ambos motores.

Revision ID: 1350
Revises: 1340
"""

import sqlalchemy as sa
from alembic import op

from app.db.types import PortableJSON

revision = "1350"
down_revision = "1340"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("profesional", sa.Column("salutem_profesional_id", sa.BigInteger(), nullable=True))
    op.add_column("profesional", sa.Column("especialidades", PortableJSON(), nullable=True))
    op.add_column("profesional", sa.Column("sucursales", PortableJSON(), nullable=True))
    op.add_column("profesional", sa.Column("primera_atencion", sa.Date(), nullable=True))
    op.add_column("profesional", sa.Column("ultima_atencion", sa.Date(), nullable=True))
    op.add_column("profesional", sa.Column("sincronizado_en", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_profesional_salutem_id", "profesional", ["salutem_profesional_id"])

    for tabla, abrev in (("control_medico", "ctrl_med"), ("ficha_clinica", "ficha_clin")):
        op.add_column(tabla, sa.Column("profesional_id", sa.BigInteger(), nullable=True))
        op.create_foreign_key(f"fk_{abrev}_profesional", tabla, "profesional", ["profesional_id"], ["id"])
        op.create_index(f"ix_{abrev}_profesional", tabla, ["profesional_id"])


def downgrade() -> None:
    for tabla, abrev in (("ficha_clinica", "ficha_clin"), ("control_medico", "ctrl_med")):
        op.drop_index(f"ix_{abrev}_profesional", table_name=tabla)
        op.drop_constraint(f"fk_{abrev}_profesional", tabla, type_="foreignkey")
        op.drop_column(tabla, "profesional_id")

    op.drop_constraint("uq_profesional_salutem_id", "profesional", type_="unique")
    op.drop_column("profesional", "sincronizado_en")
    op.drop_column("profesional", "ultima_atencion")
    op.drop_column("profesional", "primera_atencion")
    op.drop_column("profesional", "sucursales")
    op.drop_column("profesional", "especialidades")
    op.drop_column("profesional", "salutem_profesional_id")
