import contextlib
import json
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
    def no_debe_llamarse():
        raise AssertionError("no debe construir el cliente SALUTEM con el sync apagado")

    monkeypatch.setattr(cli, "get_salutem_client", no_debe_llamarse)
    assert cli_con_bd.main(["caliente"]) == 0
