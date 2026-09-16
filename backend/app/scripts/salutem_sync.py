"""Sync SALUTEM → CEPA (fase 1, solo lectura). Lo lanza el cron de la VM.

Uso (desde backend/):
    .venv/bin/python -m app.scripts.salutem_sync caliente | tibia | fria
    .venv/bin/python -m app.scripts.salutem_sync backfill [--desde AAAA-MM-DD] [--sin-verificar]
    .venv/bin/python -m app.scripts.salutem_sync vincular [--todo]
    .venv/bin/python -m app.scripts.salutem_sync estado
"""

import argparse
import json
import logging
import sys
from datetime import date, datetime, timezone
from logging.handlers import RotatingFileHandler

from app.config import get_settings
from app.db.session import SessionLocal
from app.integrations.salutem.client import get_salutem_client
from app.services.salutem_sync.estado import estado_sync
from app.services.salutem_sync.orquestador import Opciones, correr
from app.services.salutem_sync.ritmo import Ritmo


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync SALUTEM → CEPA (solo lectura)")
    modos = parser.add_subparsers(dest="modo", required=True)
    backfill = modos.add_parser("backfill", help="Carga inicial completa")
    backfill.add_argument("--desde", type=date.fromisoformat, help="No barrer antes de esta fecha")
    backfill.add_argument("--sin-verificar", action="store_true", help="Omitir la verificación por persona")
    for modo in ("caliente", "tibia", "fria"):
        modos.add_parser(modo)
    vincular = modos.add_parser("vincular", help="Solo el paso copia → ficha_clinica")
    vincular.add_argument("--todo", action="store_true", help="Revisar todas las atenciones")
    modos.add_parser("estado", help="Mostrar el estado del sync")
    return parser


def _configurar_log(ruta: str) -> None:
    if ruta:
        handler: logging.Handler = RotatingFileHandler(
            ruta, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
    else:
        handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    raiz = logging.getLogger()
    raiz.setLevel(logging.INFO)
    raiz.addHandler(handler)


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    settings = get_settings()
    _configurar_log(settings.salutem_sync_log)

    with SessionLocal() as db:
        if args.modo == "estado":
            estado = estado_sync(db, datetime.now(timezone.utc))
            print(json.dumps(estado.model_dump(mode="json"), indent=2, ensure_ascii=False))
            return 0
        if not settings.salutem_sync_habilitado:
            logging.getLogger("salutem_sync").info(
                "Sync SALUTEM deshabilitado (SALUTEM_SYNC_HABILITADO=false)"
            )
            return 0
        return correr(
            args.modo,
            db,
            get_salutem_client(),
            Ritmo(settings.salutem_sync_llamadas_por_seg),
            ahora=lambda: datetime.now(timezone.utc),
            habilitado=True,
            opciones=Opciones(
                desde=getattr(args, "desde", None),
                verificar=not getattr(args, "sin_verificar", False),
                dias_vacios_para_parar=settings.salutem_backfill_dias_vacios,
                vincular_todo=getattr(args, "todo", False),
            ),
        )


if __name__ == "__main__":
    sys.exit(main())
