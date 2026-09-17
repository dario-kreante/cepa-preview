"""Sync SALUTEM → CEPA (fase 1, solo lectura). Lo lanza el cron de la VM.

Uso (desde backend/):
    .venv/bin/python -m app.scripts.salutem_sync caliente | tibia | fria
    .venv/bin/python -m app.scripts.salutem_sync backfill [--desde AAAA-MM-DD] [--dias-futuro N] [--sin-verificar]
    .venv/bin/python -m app.scripts.salutem_sync vincular [--todo]
    .venv/bin/python -m app.scripts.salutem_sync estado
"""

import argparse
import json
import logging
import os
import sys
from datetime import date, datetime, timezone
from logging.handlers import RotatingFileHandler

from app.config import get_settings
from app.db.session import SessionLocal
from app.integrations.salutem.client import get_salutem_client
from app.services.salutem_sync.backfill import DIAS_FUTURO
from app.services.salutem_sync.estado import estado_sync
from app.services.salutem_sync.orquestador import Opciones, correr
from app.services.salutem_sync.ritmo import Ritmo


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync SALUTEM → CEPA (solo lectura)")
    modos = parser.add_subparsers(dest="modo", required=True)
    backfill = modos.add_parser("backfill", help="Carga inicial completa")
    backfill.add_argument("--desde", type=date.fromisoformat, help="No barrer antes de esta fecha")
    backfill.add_argument(
        "--dias-futuro", type=int, default=DIAS_FUTURO, help="Días hacia adelante a barrer (180)"
    )
    backfill.add_argument("--sin-verificar", action="store_true", help="Omitir la verificación por persona")
    for modo in ("caliente", "tibia", "fria"):
        modos.add_parser(modo)
    vincular = modos.add_parser("vincular", help="Solo el paso copia → ficha_clinica")
    vincular.add_argument("--todo", action="store_true", help="Revisar todas las atenciones")
    modos.add_parser("estado", help="Mostrar el estado del sync")
    return parser


def _ruta_log_por_modo(ruta: str, modo: str) -> str:
    """Un archivo de log por modo: evita que dos procesos roten el mismo archivo.

    "salutem-sync.log" + "caliente" -> "salutem-sync-caliente.log".
    """
    if not ruta:
        return ruta
    raiz, ext = os.path.splitext(ruta)
    return f"{raiz}-{modo}{ext}"


def _configurar_log(ruta: str, modo: str) -> None:
    ruta_modo = _ruta_log_por_modo(ruta, modo)
    if ruta_modo:
        handler: logging.Handler = RotatingFileHandler(
            ruta_modo, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
    else:
        handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logging.basicConfig(handlers=[handler], level=logging.INFO, force=True)
    # httpx/httpcore son muy verborrágicos en INFO (loguean cada request); no aportan nada
    # al log del sync y solo tapan lo que sí importa.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    try:
        settings = get_settings()
        _configurar_log(settings.salutem_sync_log, args.modo)

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
                    dias_futuro=getattr(args, "dias_futuro", DIAS_FUTURO),
                    dias_vacios_para_parar=settings.salutem_backfill_dias_vacios,
                    vincular_todo=getattr(args, "todo", False),
                ),
            )
    except Exception:
        logging.getLogger("salutem_sync").exception(
            "Falla inesperada en el sync SALUTEM (modo=%s)", args.modo
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
