"""Job diario de alertas (COMP-2609-06). Lo lanza el cron de la VM vía ops/vm/run-alertas.sh.

Corre en una sola ejecución el motor de plazos, las alertas de licencias y las de
recetas, con actor ``sistema`` en la auditoría. Idempotente: correrlo dos veces el
mismo día no duplica alertas.

Uso (desde backend/):
    .venv/bin/python -m app.scripts.alertas_job [--log RUTA]

Código de salida: 0 si terminó bien, 1 ante cualquier falla (queda en el log).
"""

import argparse
import logging
import sys
from logging.handlers import RotatingFileHandler

from app.config import get_settings
from app.db.session import SessionLocal
from app.services.alertas_job import correr_job_alertas

logger = logging.getLogger("alertas_job")


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Job diario de alertas (motor, licencias y recetas)")
    parser.add_argument("--log", help="Archivo de log (por defecto ALERTAS_JOB_LOG; vacío = consola)")
    return parser


def _configurar_log(ruta: str) -> None:
    handlers: list[logging.Handler] = []
    if ruta:
        archivo = RotatingFileHandler(ruta, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
        archivo.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        handlers.append(archivo)
    else:
        consola = logging.StreamHandler(sys.stderr)
        consola.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        handlers.append(consola)
    logging.basicConfig(handlers=handlers, level=logging.INFO, force=True)


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    ruta = args.log if args.log is not None else get_settings().alertas_job_log
    _configurar_log(ruta)
    try:
        with SessionLocal() as db:
            resumen = correr_job_alertas(db)
    except Exception:
        logger.exception("Falla inesperada en el job de alertas")
        print("Job de alertas: FALLÓ (ver log)", flush=True)
        return 1
    linea = (
        f"Job de alertas OK: motor={resumen['motor']} "
        f"licencias={resumen['licencias']} recetas={resumen['recetas']}"
    )
    logger.info(linea)
    print(linea, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
