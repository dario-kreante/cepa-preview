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
| `SALUTEM_SYNC_LOG` | `/home/segicepa/sige-cepa/logs/salutem-sync.log` | rota a 5 × 10 MB |

## Puesta en marcha (una vez)
Requiere aprobación explícita de Darío, la clave de producción y el aviso a DTI.

1. Desplegar el backend con el procedimiento habitual (memoria `despliegue-vm-utalca`) y aplicar migraciones:
   `cd ~/sige-cepa/backend && LD_LIBRARY_PATH=$HOME/opt/instantclient_19_26 TNS_ADMIN=$HOME/opt/tns .venv/bin/alembic upgrade head`
2. Copiar `ops/vm/run-salutem-sync.sh` a `~/sige-cepa/run-salutem-sync.sh` y `chmod +x`.
   Comparar sus `export` con los de `~/sige-cepa/run-api.sh`; deben coincidir.
3. Configurar las variables del `.env` con `SALUTEM_SYNC_HABILITADO=true`.
4. Probar: `~/sige-cepa/run-salutem-sync.sh estado` → JSON con `"atrasado": true`.
5. Carga inicial fuera de horario:
   `nohup ~/sige-cepa/run-salutem-sync.sh backfill > /dev/null 2>&1 &`
   Seguir con `tail -f ~/sige-cepa/logs/salutem-sync.log`. Se puede cortar y relanzar: retoma.
6. Al terminar, revisar el log: primer día con datos, días con error y la advertencia de
   "atenciones anteriores" (si aparece, relanzar con `--desde` más antiguo).
7. Instalar el cron: `crontab -l > ~/crontab-backup-$(date +%F).txt`, luego
   `(crontab -l; cat ops/vm/crontab-salutem-sync.txt) | crontab -` y verificar con `crontab -l`.

## Operación diaria
- Estado: `~/sige-cepa/run-salutem-sync.sh estado` o `GET /api/v1/salutem/sync/estado` (Coordinación).
- `atrasado: true` → revisar `~/sige-cepa/logs/salutem-sync.log` y la última ejecución con `estado = error`.
- `con_errores` → algún día fue rechazado por SALUTEM; la ventana siguiente lo reintenta.
- Revincular todo tras cambiar la regla de ventana: `run-salutem-sync.sh vincular --todo`.

## Apagar
`SALUTEM_SYNC_HABILITADO=false` en el `.env`. El cron sigue corriendo pero cada ejecución sale sin hacer nada.
Para retirar del todo: quitar las tres líneas del crontab.

## Validación en QA (antes de producción)
Registrar aquí los resultados de la Task 15 del plan.
