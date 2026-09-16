# Runbook — Sync SALUTEM (fase 1, solo lectura)

Diseño: `docs/superpowers/specs/2026-09-16-salutem-sync-fase1-design.md`.

## Qué hace
- Copia todo SALUTEM (empresa 96) a las tablas `salutem_persona`, `salutem_cita`, `salutem_atencion`.
- Vincula las atenciones con `ficha_clinica` por RUT y ventana del ingreso.
- Nunca escribe en SALUTEM (D12).

## Variables (`~/sige-cepa/backend/.env`)

| Variable | Valor en la VM | Nota |
|---|---|---|
| `SALUTEM_BASE_URL` | `https://api.salutem.cl/api/integraciones/salutem` (PROD) | QA: `https://qa.salutem.cl/...` |
| `SALUTEM_EMPRESA` | `96` | |
| `SALUTEM_API_KEY` | (clave de producción) | no versionar |
| `SALUTEM_SYNC_HABILITADO` | `true` | `false` apaga todo sin tocar el cron |
| `SALUTEM_SYNC_LLAMADAS_POR_SEG` | `2` | ajustar con el límite que confirme FabricApp |
| `SALUTEM_BACKFILL_DIAS_VACIOS` | `365` | |
| `SALUTEM_SYNC_LOG` | `/home/segicepa/sige-cepa/logs/salutem-sync.log` | rota a 5 × 10 MB; un archivo por modo, ver abajo |

## Puesta en marcha (una vez)
Requiere aprobación explícita de Darío, la clave de producción y el aviso a DTI.

1. Desplegar el backend con el procedimiento habitual (memoria `despliegue-vm-utalca`) y aplicar migraciones:
   `cd ~/sige-cepa/backend && LD_LIBRARY_PATH=$HOME/opt/instantclient_19_26 TNS_ADMIN=$HOME/opt/tns .venv/bin/alembic upgrade head`
2. `ops/` no viaja en el deploy (solo se copian `backend/` y el build del frontend), así que
   hay que copiar estos dos archivos aparte desde la máquina de desarrollo (macOS —
   `COPYFILE_DISABLE=1` evita que scp arrastre metadatos `._*`):
   ```
   COPYFILE_DISABLE=1 scp ops/vm/run-salutem-sync.sh ops/vm/crontab-salutem-sync.txt \
       segicepa@192.168.22.183:~/sige-cepa/
   ```
   Luego, ya en la VM: `chmod +x ~/sige-cepa/run-salutem-sync.sh`.
   Comparar sus `export` con los de `~/sige-cepa/run-api.sh`; deben coincidir.
3. Configurar las variables del `.env` con `SALUTEM_SYNC_HABILITADO=true` (todos los modos,
   incluido `vincular`, salen sin hacer nada si falta o está en `false`).
4. Probar: `~/sige-cepa/run-salutem-sync.sh estado` → JSON con `"atrasado": true`.
   Corrido a mano (con terminal) imprime directo; por cron, todo lo previo a que el script
   configure su log cae en `~/sige-cepa/logs/salutem-sync-cron.log`.
5. Carga inicial fuera de horario:
   `nohup ~/sige-cepa/run-salutem-sync.sh backfill > /dev/null 2>&1 &`
   Seguir con `tail -F ~/sige-cepa/logs/salutem-sync-backfill.log` (un archivo por modo; ver
   la sección de logs más abajo). Se puede cortar y relanzar: retoma.
6. Al terminar, revisar el log: primer día con datos, días con error y la advertencia de
   "atenciones anteriores" (si aparece, relanzar con `--desde` más antiguo).
7. Instalar el cron de forma idempotente (usar rutas absolutas, no relativas al checkout):
   ```
   crontab -l > ~/crontab-backup-$(date +%F).txt
   crontab -l | grep -v 'run-salutem-sync' > /tmp/ct.salutem
   cat ~/sige-cepa/crontab-salutem-sync.txt >> /tmp/ct.salutem
   crontab /tmp/ct.salutem
   crontab -l
   ```
   El `grep -v` también descarta los comentarios del fragmento porque todos incluyen la
   marca `run-salutem-sync` — por eso se puede volver a correr este bloque sin duplicar
   entradas (por ejemplo tras editar `crontab-salutem-sync.txt` y copiarlo de nuevo).

   Para revertir: `crontab -l | grep -v 'run-salutem-sync' | crontab -` (o restaurar el
   backup del paso 1 con `crontab ~/crontab-backup-<fecha>.txt`).

## Logs
- Cada modo escribe su propio archivo, derivado de `SALUTEM_SYNC_LOG`: con
  `salutem-sync.log` configurado, `caliente` cae en `salutem-sync-caliente.log`, `backfill`
  en `salutem-sync-backfill.log`, etc. Es así para que dos modos corriendo a la vez no
  compitan por rotar el mismo archivo. Seguirlos con `tail -F` (no `-f`): rota por tamaño
  y `-F` reabre el archivo nuevo en vez de quedarse mirando el inodo viejo.
- `~/sige-cepa/logs/salutem-sync-cron.log` es aparte: solo recibe lo que revienta antes de
  que el script logre configurar su log por modo (crashes, tracebacks). Revisarlo de vez en
  cuando y truncarlo si crece: `: > ~/sige-cepa/logs/salutem-sync-cron.log`.
- El lock de cada modo (`flock`, para que no se apilen dos ejecuciones del mismo) vive en
  `~/sige-cepa/logs/.salutem-sync-<modo>.lock`.

## Operación diaria
- Estado: `~/sige-cepa/run-salutem-sync.sh estado` o `GET /api/v1/salutem/sync/estado` (Coordinación).
- `atrasado: true` → revisar `~/sige-cepa/logs/salutem-sync-caliente.log` y la última ejecución con `estado = error`.
- `con_errores` → algún día fue rechazado por SALUTEM; la ventana siguiente lo reintenta.
- Revincular todo tras cambiar la regla de ventana: `run-salutem-sync.sh vincular --todo`
  (también requiere `SALUTEM_SYNC_HABILITADO=true`).

## Apagar
`SALUTEM_SYNC_HABILITADO=false` en el `.env`. El cron sigue corriendo pero cada ejecución
(incluida `vincular`) sale sin hacer nada.
Para retirar del todo: `crontab -l | grep -v 'run-salutem-sync' | crontab -`.

## Validación en QA (antes de producción)
Registrar aquí los resultados de la Task 15 del plan.
