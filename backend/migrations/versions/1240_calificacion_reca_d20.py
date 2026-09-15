"""D20: el estado RECA del control médico pasa a ser la calificación RECA

Decisiones v5 D20 fija un catálogo único de calificación RECA
(EP · EC · AT · AC · NPE · No aplica) para el control médico y la RECA del
reintegro. El control guardaba un estado de flujo (pendiente/aprobado/
rechazado/en_proceso) que no tiene equivalente en la calificación: esos valores
se dejan en blanco y solo se conserva `no_aplica`.

Sin cambios de esquema: `estado_reca` es String(20) y `reca.tipo_reca`
String(10), y ambos admiten el catálogo nuevo. Los AT/EP del reintegro ya son
valores válidos.

Revision ID: 1240
Revises: 1230
"""

from alembic import op

revision = "1240"
down_revision = "1230"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE control_medico SET estado_reca = NULL "
        "WHERE estado_reca IN ('pendiente', 'aprobado', 'rechazado', 'en_proceso')"
    )


def downgrade() -> None:
    # El estado de flujo borrado no se puede recuperar; solo se quitan los valores
    # que el catálogo anterior no admitía.
    op.execute(
        "UPDATE control_medico SET estado_reca = NULL "
        "WHERE estado_reca IN ('EP', 'EC', 'AT', 'AC', 'NPE')"
    )
    op.execute(
        "UPDATE reca SET tipo_reca = 'AT' WHERE tipo_reca IN ('EC', 'AC', 'NPE', 'no_aplica')"
    )
