import contextlib
import json
import logging
from datetime import date

import pytest

from app.config import Settings
from app.scripts import salutem_sync as cli


@pytest.fixture
def cli_con_bd(monkeypatch, db_session):
    monkeypatch.setattr(cli, "SessionLocal", lambda: contextlib.nullcontext(db_session))
    monkeypatch.setattr(cli, "get_settings", lambda: Settings(_env_file=None))
    return cli


def test_parser_backfill_con_opciones():
    args = cli.construir_parser().parse_args(["backfill", "--desde", "2023-01-01", "--sin-verificar"])
    assert (args.modo, args.desde, args.sin_verificar) == ("backfill", date(2023, 1, 1), True)


def test_parser_rechaza_modos_desconocidos():
    with pytest.raises(SystemExit):
        cli.construir_parser().parse_args(["tempestad"])


def test_estado_imprime_json(cli_con_bd, capsys):
    assert cli_con_bd.main(["estado"]) == 0
    assert "atrasado" in json.loads(capsys.readouterr().out)


def test_con_el_sync_apagado_sale_en_cero_sin_red(cli_con_bd, monkeypatch):
    # Robusto a cómo esté el entorno real: lo que importa es lo que devuelve get_settings
    # (parcheado en el fixture), no si SALUTEM_SYNC_HABILITADO quedó seteada en el shell.
    monkeypatch.delenv("SALUTEM_SYNC_HABILITADO", raising=False)

    def no_debe_llamarse():
        raise AssertionError("no debe construir el cliente SALUTEM con el sync apagado")

    monkeypatch.setattr(cli, "get_salutem_client", no_debe_llamarse)
    assert cli_con_bd.main(["caliente"]) == 0


def test_ruta_de_log_por_modo_deriva_del_stem():
    assert cli._ruta_log_por_modo("salutem-sync.log", "caliente") == "salutem-sync-caliente.log"
    assert cli._ruta_log_por_modo("/x/y/salutem-sync.log", "backfill") == "/x/y/salutem-sync-backfill.log"
    assert cli._ruta_log_por_modo("", "caliente") == ""


def test_configurar_log_baja_el_nivel_de_httpx(tmp_path):
    ruta = str(tmp_path / "salutem-sync-caliente.log")
    cli._configurar_log(ruta, "caliente")
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING


def test_main_devuelve_1_si_la_bd_no_responde(monkeypatch):
    def truena():
        raise RuntimeError("BD inalcanzable")

    monkeypatch.setattr(cli, "SessionLocal", truena)
    monkeypatch.setattr(cli, "get_settings", lambda: Settings(_env_file=None))
    assert cli.main(["estado"]) == 1


def test_parser_backfill_dias_futuro():
    parser = cli.construir_parser()
    assert parser.parse_args(["backfill"]).dias_futuro == 180
    assert parser.parse_args(["backfill", "--dias-futuro", "30"]).dias_futuro == 30


@pytest.fixture
def cli_habilitado(monkeypatch, db_session):
    monkeypatch.setattr(cli, "SessionLocal", lambda: contextlib.nullcontext(db_session))
    monkeypatch.setattr(
        cli, "get_settings", lambda: Settings(_env_file=None, salutem_sync_habilitado=True)
    )
    monkeypatch.setattr(cli.time, "sleep", lambda s: None)
    # alembic (fileConfig) desactiva los loggers existentes al migrar la BD de pruebas.
    monkeypatch.setattr(logging.getLogger("salutem_sync"), "disabled", False)
    return cli


def test_vincular_a_mano_imprime_el_resultado(cli_habilitado, capsys):
    assert cli_habilitado.main(["vincular", "--todo"]) == 0
    assert "Modo vincular terminado" in capsys.readouterr().out


def test_vincular_espera_a_que_se_libere_el_lease(cli_habilitado, monkeypatch, capsys):
    codigos = iter([cli.OMITIDO, cli.OMITIDO, 0])
    monkeypatch.setattr(cli, "correr", lambda *a, **k: next(codigos))

    assert cli_habilitado.main(["vincular", "--todo"]) == 0
    assert capsys.readouterr().out.count("otro proceso del sync está corriendo") == 2


def test_vincular_se_rinde_si_el_lease_no_se_libera(cli_habilitado, monkeypatch, capsys):
    monkeypatch.setattr(cli, "correr", lambda *a, **k: cli.OMITIDO)

    assert cli_habilitado.main(["vincular", "--todo", "--esperar", "1"]) == cli.OMITIDO
    assert "no se vinculó nada" in capsys.readouterr().out
