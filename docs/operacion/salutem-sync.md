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
   la sección de logs más abajo). Se puede cortar y relanzar: retoma (salta los días ya
   registrados), pero:
   - Una ejecución cortada (`kill`, `timeout`/SIGTERM, caída de la VM) no suelta el lease de
     la base: queda tomado hasta 30 minutos. Si se relanza antes, la nueva ejecución registra
     `omitida` y sale con código 0 sin hacer nada. Esperar 30 minutos desde el corte antes de
     relanzar; si hay dudas, revisar con `run-salutem-sync.sh estado` (y el log del modo) que
     el relanzamiento no haya quedado como `omitida`.
   - Cada relanzamiento vuelve a barrer los 180 días futuros (~14 min a 2 llamadas/s) antes
     de seguir con el pasado.
6. Al terminar, revisar el log: primer día con datos, días con error y la advertencia de
   "atenciones anteriores" (si aparece, relanzar con `--desde` más antiguo).
   Sin `--desde`, lo normal es que el backfill termine porque SALUTEM rechaza las fechas
   antiguas: el log muestra `BackfillAbortadoError` con la fecha D donde abortó, y en ese
   caso **no** corrieron la verificación por persona ni la vinculación. Relanzar con
   `--desde` = D + 1 día (los días ya registrados se saltan) para que ambas se ejecuten.
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
   backup hecho en la primera línea de este paso 7 con
   `crontab ~/crontab-backup-<fecha>.txt`).

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
- `con_errores` → la ejecución terminó pero algo quedó sin traer: un día rechazado por
  SALUTEM, un registro puntual rechazado (una cita, persona o atención), o un error de
  vinculación. El detalle está en el campo `error` de esa ejecución. La ventana siguiente
  lo reintenta. Solo una credencial rechazada o SALUTEM caído tras los reintentos detienen
  la ejecución (`estado = error`).
- Cada noche la `fria` (~35–40 min) tiene el lease: entre ~03:30 y 04:15 las `caliente`
  quedan `omitida` y `estado` puede mostrar `atrasado: true`. Es esperado; si sigue atrasado
  pasadas las 04:30, revisar.
- Revincular todo tras cambiar la regla de ventana: `run-salutem-sync.sh vincular --todo`
  (también requiere `SALUTEM_SYNC_HABILITADO=true`). Hazlo también después de desplegar un
  cambio en cómo se arman fichas o controles desde la copia.
  Corrido a mano, `vincular` imprime el resultado en la consola. Si el cron tiene el lease,
  reintenta cada 20 s hasta 5 minutos (`--esperar N` para cambiar el límite, `0` para no
  esperar). Si no lo consigue, avisa "omitido" y sale con código 3: no vinculó nada. `backfill`
  omitido por lease también sale con 3. Los modos del cron siguen saliendo con 0.

## Límites conocidos
- Una atención borrada en SALUTEM con fecha de más de 30 días atrás no se detecta en la
  operación diaria (la `fria` relee solo el último mes): solo la marca una nueva
  verificación de backfill.
- Achicar la ventana de un ingreso o corregir el RUT de un paciente no desvincula las fichas
  ya vinculadas. Las fichas que correspondan tras corregir un RUT sí se vinculan en la `fria`
  de esa noche.

## Apagar
`SALUTEM_SYNC_HABILITADO=false` en el `.env`. El cron sigue corriendo pero cada ejecución
(incluida `vincular`) sale sin hacer nada.
Para retirar del todo: `crontab -l | grep -v 'run-salutem-sync' | crontab -`.

## Validación en QA (antes de producción)

Hecha el 2026-09-16 contra `qa.salutem.cl`, empresa 96, con una BD Postgres local (`cepa_salutem_qa`). Solo lectura.

| Verificación | Resultado |
|---|---|
| `obtener_persona` por `persona_id` | ✅ Devuelve la persona; coincide con `resolver_persona` por RUT |
| Estabilidad del hash (dos barridos seguidos de 2025-01-22) | ✅ Vuelta 1: 52 citas, 141 registros nuevos, 98 llamadas. Vuelta 2: 0 nuevos, 0 cambiados, 9 llamadas. `CAMPOS_VOLATILES` queda vacío |
| Re-lectura de atenciones (`refrescar_atenciones`) | ✅ 0 cambios falsos |
| Atenciones fuera del estado Atendido | ✅ Ninguna en la muestra (5 Anuladas, 3 No Asiste; sin citas en otros estados ese día). `ESTADOS_CON_ATENCION` queda solo Atendido. Muestra chica: revisar en producción |
| `backfill --desde 2026-09-01` | ✅ `ok`, 196 días (180 futuros), 2.808 llamadas en 26 min (~1,8 llamadas/s efectivas). El rango no tenía citas; la verificación por persona recuperó 999 atenciones históricas (2023-02-16 a 2026-01-21) |
| `caliente` | ✅ `ok`, 27 llamadas en 40 s |
| Vinculación con un paciente CEPA de prueba (RUT de una persona de QA, ingreso desde 2023-01-01) | ✅ 78 atenciones → 78 fichas; segunda vinculación completa: 0 nuevas, 0 actualizadas |
| `estado` | ✅ `atrasado: false`, 0 atenciones pendientes |

Hallazgo corregido: el aviso de "atenciones anteriores" comparaba contra el primer día con citas y no se emitía si el rango barrido no tenía ninguna (caso de este backfill). Ahora compara contra el primer día barrido.

Estimaciones para producción: la API responde ~0,5–0,6 s por llamada, así que el ritmo real ronda 1,8 llamadas/s aunque el límite configurado sea 2. En QA los datos llegan hasta 2026-01-21, más de 7 meses sin citas: en producción conviene revisar el log del backfill por si se detiene antes de la historia real, y apoyarse en la verificación por persona.
