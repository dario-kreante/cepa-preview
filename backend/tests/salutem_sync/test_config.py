from app.config import Settings


def test_el_sync_viene_apagado_y_con_ritmo_conservador():
    s = Settings(_env_file=None)
    assert s.salutem_sync_habilitado is False
    assert s.salutem_sync_llamadas_por_seg == 2.0
    assert s.salutem_backfill_dias_vacios == 365
    assert s.salutem_sync_log == ""
