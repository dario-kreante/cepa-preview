# Runbook — Job diario de alertas (COMP-2609-06)

## Qué hace
Una sola ejecución de `app.scripts.alertas_job` corre, en este orden:

1. El motor de plazos perentorios (`ejecutar_job_alertas`) → tabla `alerta_notif`
   (ODA, EPT, ISL, licencias, recetas, controles, consentimiento).
2. Las alertas de vencimiento de licencias → tabla `alerta_licencia`.
3. Las alertas de revisión de recetas → tabla `alerta`.

La auditoría queda con `actor = sistema`. Es idempotente: correrlo dos veces el mismo día no
duplica alertas. Los umbrales y festivos se leen de la BD en cada ejecución
(`config_alerta` y `festivo`, editables en `/config-alertas` por Coordinación, COMP-2609-07):
un cambio aplica en la siguiente corrida sin reiniciar nada.

Los botones "Generar alertas" (Licencias) y `POST /api/v1/alertas/ejecutar-job` se conservan
para probar a mano; comparten la misma idempotencia.

## Variables (`~/sige-cepa/backend/.env`)

| Variable | Valor en la VM | Nota |
|---|---|---|
| `ALERTAS_JOB_LOG` | `/home/segicepa/sige-cepa/logs/alertas-job.log` | rota a 5 × 5 MB; vacío = consola |

## Instalación (una vez)

1. Desplegar el backend con el procedimiento habitual y aplicar migraciones (crea
   `config_alerta` y `festivo`, migración 1290):
   `cd ~/sige-cepa/backend && LD_LIBRARY_PATH=$HOME/opt/instantclient_19_26 TNS_ADMIN=$HOME/opt/tns .venv/bin/alembic upgrade head`
2. `ops/` no viaja en el deploy; copiar los dos archivos desde la máquina de desarrollo:
   ```
   COPYFILE_DISABLE=1 scp ops/vm/run-alertas.sh ops/vm/crontab-alertas.txt \
       segicepa@192.168.22.183:~/sige-cepa/
   ```
   En la VM: `chmod +x ~/sige-cepa/run-alertas.sh`. Sus `export` deben coincidir con los de
   `~/sige-cepa/run-api.sh`.
3. Agregar `ALERTAS_JOB_LOG=/home/segicepa/sige-cepa/logs/alertas-job.log` al `.env`.
4. Confirmar la zona horaria de la VM: `date` debe mostrar hora de Chile (`-03`/`-04`). Si la
   VM está en UTC, ajustar la hora del fragmento antes de instalarlo (07:00 Chile = 10:00 u
   11:00 UTC según horario de verano) — no usar `CRON_TZ`, que afectaría a las otras entradas.
5. Probar a mano: `~/sige-cepa/run-alertas.sh` → imprime
   `Job de alertas OK: motor=N licencias=N recetas=N` y sale con código 0. Una segunda corrida
   inmediata debe dar `motor=0 licencias=0 recetas=0`.
6. Instalar el cron de forma idempotente (no borra las otras entradas):
   ```
   crontab -l > ~/crontab-backup-$(date +%F).txt
   crontab -l | grep -v 'run-alertas' > /tmp/ct.alertas
   cat ~/sige-cepa/crontab-alertas.txt >> /tmp/ct.alertas
   crontab /tmp/ct.alertas
   crontab -l
   ```
   El `grep -v` descarta también los comentarios del fragmento (todos llevan la marca
   `run-alertas`), así que el bloque se puede repetir sin duplicar entradas.

## Verificación (al día hábil siguiente)
- `tail -n 20 ~/sige-cepa/logs/alertas-job.log` muestra la línea `Job de alertas OK` de las 07:00.
- En la BD: `SELECT actor, entity, created_at FROM audit_log WHERE actor = 'sistema' ORDER BY id DESC`
  (o la pantalla de Auditoría filtrando por actor `sistema`) muestra las trazas del job si
  hubo alertas nuevas; `alerta_notif` tiene filas con `generada_en` de esa mañana.
- `~/sige-cepa/logs/alertas-cron.log` solo recibe lo que falle antes de configurar el log
  (tracebacks de arranque). Si crece, revisar y truncar: `: > ~/sige-cepa/logs/alertas-cron.log`.
- El lock (`flock`) vive en `~/sige-cepa/logs/.alertas.lock`; si ya hay una ejecución
  corriendo, la nueva sale con código 0 y un aviso en `alertas-cron.log`.

## Reversión
- Quitar solo esta entrada: `crontab -l | grep -v 'run-alertas' | crontab -`
  (o restaurar el backup del paso 6: `crontab ~/crontab-backup-<fecha>.txt`).
- Las tablas `config_alerta` y `festivo` pueden quedar: si se vacían, el motor usa los valores
  por defecto del código. Revertir la migración (`alembic downgrade 1280`) solo si se revierte
  también el código que las lee.
