# PASO A PRODUCCIÓN — SIGE-CEPA
## Procedimiento para Infraestructura (QA → PROD, posterior a CAB)

| | |
|---|---|
| Versión del documento | 1.0 (borrador) |
| Fecha | Noviembre 2026 |
| Versión a desplegar | `main` 878eed8, migración de BD 1580 (es la versión que está hoy en QA) |
| Complementa a | *Manual de Instalación SIGE-CEPA* (los pasos técnicos detallados están en ese documento) |

> Los datos marcados **[PENDIENTE: …]** los tiene que entregar DTI o el CEPA antes de presentar en CAB.

## Descripción

Este documento describe los pasos para desplegar **SIGE-CEPA** (Sistema de Gestión del Centro de Psicología Aplicada) en el servidor de producción, a partir de la versión aprobada en QA.

## El sistema consta de los ambientes

1. **Base de datos PROD:** **[PENDIENTE: host / SID / esquema Oracle 19c]**
2. **Servidor productivo:** **[PENDIENTE: hostname e IP]**. Corre nginx, la API (uvicorn) y los procesos programados.
3. **Dominio productivo:** **[PENDIENTE: p. ej. `sige-cepa.utalca.cl`]**, con HTTPS.
4. **Integraciones externas:**
    - SALUTEM, API de solo lectura: **[PENDIENTE: URL de producción]**.
    - IdP institucional SAML: `idprovider.utalca.cl`.
    - Relay SMTP para el correo de alertas: **[PENDIENTE]**.

## Conexiones a los servidores

### Servidor QA (origen)
- **Servidor:** `segicepa-qa.utalca.cl` (192.168.21.202)
- **Puerto SSH:** 22
- **Protocolo:** SSH / SFTP
- **Usuario:** `segicepa`
- **Directorios:** `/home/segicepa/sige-cepa` (backend, scripts, logs, `.env`) y `/var/www/sige-cepa` (frontend)

### Servidor PROD (destino)
- **Servidor:** **[PENDIENTE]**
- **Puerto SSH:** 22
- **Protocolo:** SSH / SFTP
- **Usuario:** `segicepa`, con sudo
- **Directorios:** los mismos que en QA

### Base de datos QA
- **Host:** `oracle19c-test.utalca.cl`
- **Puerto:** 1521
- **SID:** `dbutal9`
- **Esquema / usuario:** `UTCEPA01`

### Base de datos PROD
- **Host:** **[PENDIENTE]**
- **Puerto:** 1521
- **SID:** **[PENDIENTE]**. Ojo: es un SID, no un service name (ver el manual, punto 4.3).
- **Esquema / usuario:** **[PENDIENTE: p. ej. `UTCEPA01` en el servidor productivo]**

---

## Claves y credenciales

**Ninguna clave va en este documento ni en el paquete de la versión.** Cada una se escribe directamente en `/home/segicepa/sige-cepa/backend/.env` (permisos 600) en el servidor PROD.

| Credencial | Variable en .env | Quién la gestiona |
|---|---|---|
| Clave del esquema Oracle PROD | `DATABASE_URL` | DBA de DTI, con el conducto formal |
| API key de SALUTEM PROD | `SALUTEM_API_KEY` | **[PENDIENTE: responsable SALUTEM / CEPA]** |
| Cuenta del relay SMTP | `SMTP_USERNAME` / `SMTP_PASSWORD` | **[PENDIENTE: DTI]** |
| Certificado público del IdP | `SAML_IDP_CERT` | DTI. Es público, no es secreto. |
| Secreto de firma de tokens | `JWT_SECRET` | Se genera en el servidor (`openssl rand -hex 32`) y es exclusivo de PROD |
| Certificado SSL y llave del dominio | `/etc/nginx/ssl/` | **[PENDIENTE: DTI / Plataformas]** |

### Solicitud de la clave Oracle
La clave se pide por el conducto formal de DTI para claves Oracle (aprobación de la Jefatura de Sistemas y entrega por el DBA). Los nombres de quienes intervienen están en el documento de DTI, no en este repositorio.

---

## Requisitos previos (antes del día del paso)

| # | Requisito | Responsable | Estado |
|---|---|---|---|
| 1 | VM PROD con Debian 12, usuario `segicepa` con sudo, zona horaria America/Santiago | DTI / Infraestructura | **[PENDIENTE]** |
| 2 | Registro DNS del dominio productivo apuntando a la VM | DTI | **[PENDIENTE]** |
| 3 | Certificado SSL del dominio | DTI / Plataformas | **[PENDIENTE]** |
| 4 | Esquema Oracle PROD **vacío**, con su clave | DBA | **[PENDIENTE]** |
| 5 | Reglas de red: VM → Oracle (1521), VM → SALUTEM (443), VM → `idprovider.utalca.cl` (443), VM → relay SMTP (587) | DTI / Redes | **[PENDIENTE]** |
| 6 | SIGE registrado como Service Provider SAML en `idprovider.utalca.cl`, con la URL ACS de PROD | DTI | **[PENDIENTE]** |
| 7 | Credenciales de SALUTEM productivo | CEPA / SALUTEM | **[PENDIENTE]** |
| 8 | Relay SMTP y cuenta remitente (`cepa-alertas@utalca.cl` o la que se defina) | DTI | **[PENDIENTE]** |
| 9 | Paquete de la versión `sige-cepa-878eed8.tar.gz`, con su checksum SHA-256 | Kreante | Se entrega con la aprobación del CAB |
| 10 | Lista de usuarios iniciales y sus roles (Coordinación, Administrativo, Médico, Psicólogo, etc.) | CEPA | **[PENDIENTE]** |

---

## RESPALDO

Al ser la **primera instalación**, en PROD no hay una versión anterior que respaldar. Para futuras versiones:

- **Aplicación:** copiar los directorios actuales con fecha antes de reemplazarlos.
  ```bash
  cp -a ~/sige-cepa ~/sige-cepa-backup-AAAAMMDD
  cp -a /var/www/sige-cepa ~/sige-cepa-web-backup-AAAAMMDD
  ```
- **Base de datos:** el DBA exporta el esquema PROD con Data Pump (`expdp`) antes de aplicar migraciones. Si una migración modifica datos, también se exportan aparte las tablas afectadas.

---

## 1.0 PASO A PRODUCCIÓN — SERVIDOR DE APLICACIÓN

**Se instala desde el paquete de la versión, no clonando la VM de QA.** La VM de QA lleva su `.env`, su alias TNS y su crontab apuntando a la base y a SALUTEM de QA, y además datos de prueba en los logs. Si se clonara, PROD podría quedar escribiendo en QA, o QA en PROD, sin que se note.

> Si Infraestructura prefiere clonar la VM de QA, como se hizo con DAFE, antes de arrancar cualquier servicio en el clon hay que hacer **obligatoriamente** los pasos 1.3 y 1.4. Además hay que **borrar** `~/sige-cepa/logs/*`, `~/.cepa-oracle-qa.pwd` y el respaldo de `.env` de QA.

### 1.1 Software base
Seguir el *Manual de Instalación*, secciones 3 y 4: nginx, uv, Python 3.12, Oracle Instant Client 19.26 y el alias TNS `CEPAPROD`.

### 1.2 Código
1. Copiar el paquete al servidor y comprobar su checksum:
   ```bash
   sha256sum sige-cepa-878eed8.tar.gz   # debe coincidir con el entregado por Kreante
   ```
2. Descomprimirlo e instalar las dependencias (manual, sección 5).
3. Copiar el frontend a `/var/www/sige-cepa`.

### 1.3 Configuración (.env)
1. Crear `/home/segicepa/sige-cepa/backend/.env` a partir de `.env.example` (manual, sección 6), con permisos 600.
2. Valores obligatorios en PROD: `ENTORNO=prod`, `DATABASE_URL` hacia `CEPAPROD`, `FRONTEND_URL` y `CORS_ORIGINS` con el dominio productivo, y un `JWT_SECRET` nuevo.
3. La clave Oracle la ingresa quien la recibió del DBA, directamente en el servidor.
4. SALUTEM, SMTP y SAML: con los datos de producción de la tabla de credenciales.
5. Verificar que **ningún** valor apunte a QA:
   ```bash
   grep -inE 'qa|test|192\.168\.21\.202' ~/sige-cepa/backend/.env ~/opt/tns/tnsnames.ora
   ```
   El único resultado aceptable es `SALUTEM_BASE_URL`, **solo** si SALUTEM confirma que PROD usa esa misma URL.

### 1.4 nginx y HTTPS
Seguir el manual, sección 7: certificados en `/etc/nginx/ssl/`, sitio `sige-cepa`, `nginx -t` y `reload`.

### 1.5 Servicios
1. Crear y habilitar el servicio `sige-cepa-api` (manual, 8.3).
2. Comprobar que el puerto 8000 escucha **solo** en 127.0.0.1:
   ```bash
   ss -ltnp | grep 8000
   ```

---

## 2.0 PASO A PRODUCCIÓN — BASE DE DATOS ORACLE

### 2.1 Creación del esquema
**No se clona el esquema de QA.** QA tiene pacientes y fichas de prueba creados durante la validación. En PROD el esquema se crea vacío con las migraciones de la aplicación, que dejan exactamente la estructura aprobada (48 tablas, versión 1580) y los datos de referencia que el sistema necesita.

```bash
cd ~/sige-cepa/backend
export LD_LIBRARY_PATH=$HOME/opt/instantclient_19_26 TNS_ADMIN=$HOME/opt/tns
.venv/bin/alembic upgrade head
.venv/bin/alembic current        # debe mostrar: 1580 (head)
```

**[PENDIENTE: confirmar con el CEPA que no hay que migrar ningún dato de QA a PROD. Si hubiera, por ejemplo usuarios o casos reales ingresados durante QA, el DBA exporta solo esas tablas y se documenta aparte.]**

### 2.2 Datos iniciales
1. Crear el primer usuario de Coordinación (manual, 8.2).
2. Ese usuario crea las cuentas de la lista entregada por el CEPA (requisito 10).
3. Carga inicial desde SALUTEM (manual, 8.5): `backfill`, luego `vincular --todo` y luego `estado`. Esto trae personas, citas y el catálogo de convenios.

### 2.3 Verificación del esquema
- `alembic current` = `1580 (head)`.
- El DBA confirma que en el esquema PROD hay 49 tablas: las 48 de la aplicación más `alembic_version`.

---

## 3.0 PROCESOS PROGRAMADOS

Instalar el crontab del usuario `segicepa` (manual, 8.4):
- Sincronización SALUTEM: caliente cada 5 minutos, tibia cada hora y fría una vez al día **[PENDIENTE: horario según disponibilidad de SALUTEM PROD]**.
- Job de alertas: de lunes a viernes a las 07:00.

**Activarlos solo después de la verificación del punto 4.0.**

---

## 4.0 VERIFICACIÓN POST-DESPLIEGUE

1. `https://[DOMINIO]` carga la pantalla de inicio de sesión con certificado válido, y `http://` redirige a `https://`.
2. `https://[DOMINIO]/health` responde HTTP 200.
3. El usuario de Coordinación inicia sesión y ve el dashboard.
4. El login institucional (SAML) devuelve al sistema autenticado.
5. `run-salutem-sync.sh estado` muestra un ciclo OK.
6. Llega un correo de alerta de prueba a una cuenta del CEPA.
7. Sin errores en:
    - `/var/log/nginx/sige-cepa.error.log`
    - `journalctl -u sige-cepa-api`
    - `~/sige-cepa/logs/`
8. Validación funcional breve con el CEPA: buscar un paciente, abrir su ficha y generar un reporte.

---

## 5.0 ROLLBACK (en caso de falla o indisponibilidad)

**Primera instalación.** No hay versión previa a la que volver; el CEPA sigue operando como hasta hoy.
1. Detener los servicios: `sudo systemctl stop sige-cepa-api` y comentar el crontab.
2. Quitar el sitio de nginx, o dejarlo con una página de mantenimiento.
3. Revisar la causa con Kreante. Si fuera necesario, el DBA vacía el esquema PROD para reinstalar desde cero.

**Versiones posteriores:**
1. Detener la API.
2. Restaurar `~/sige-cepa-backup-AAAAMMDD` y `~/sige-cepa-web-backup-AAAAMMDD`.
3. Si la versión aplicó migraciones, se puede hacer una de dos cosas:
    - `alembic downgrade <versión anterior>`, si la migración lo permite.
    - Que el DBA restaure el export de Data Pump tomado en el respaldo.
4. Levantar la API y verificar:
    - Los logs de nginx y de la API.
    - Que el dominio resuelve.
    - La conexión con Oracle (`/health` y el inicio de sesión).
    - La comunicación con SALUTEM (`run-salutem-sync.sh estado`).
    - El login SAML.

---

## 6.0 CONTACTOS

| Rol | Nombre | Para qué |
|---|---|---|
| Coordinación DTI del proyecto | [ver documento de DTI] | Coordinación del CAB y del paso a PROD |
| Jefe Unidad de Sistemas | [ver documento de DTI] | Aprobación de claves Oracle |
| Jefe Unidad de Plataformas | [ver documento de DTI] | Servidor, red, certificados |
| DBA | [ver documento de DTI] | Esquema Oracle PROD, claves, respaldos |
| Contraparte CEPA | María del Pilar García Zerene | Validación funcional y lista de usuarios |
| Proveedor (Kreante) | Darío Ramírez | Paquete de la versión, soporte del despliegue |
