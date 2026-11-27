# MANUAL DE INSTALACIÓN
## SIGE-CEPA — Sistema de Gestión del Centro de Psicología Aplicada
### Backend FastAPI (Python) + Frontend React, sobre Oracle 19c

| | |
|---|---|
| Versión del documento | 1.0 (borrador) |
| Fecha | Noviembre 2026 |
| Versión del sistema | `main` 878eed8 (migración de BD 1580) |
| Clasificación | Uso interno |
| Elaborado por | Kreante |

> Los datos marcados **[PENDIENTE: …]** son del ambiente productivo y todavía no los ha entregado DTI. Hay que completarlos antes de presentar en CAB.

---

## 1. Introducción

Este documento describe cómo instalar y configurar SIGE-CEPA en un ambiente nuevo. El sistema tiene dos partes:

- **Backend:** API REST en Python 3.12 con FastAPI, servida por uvicorn. Se conecta a Oracle 19c con `python-oracledb` en **modo Thick** (Oracle Instant Client), y el esquema se administra con migraciones Alembic.
- **Frontend:** aplicación web React 19 compilada con Vite. El resultado son archivos estáticos que sirve nginx.

nginx publica el frontend y hace de proxy inverso hacia la API (`/api/` y `/health`) en `127.0.0.1:8000`. Así, el navegador solo habla con nginx.

Además corren tres procesos programados con cron:

- La sincronización de solo lectura con **SALUTEM** (modos caliente, tibia y fría).
- El **job diario de alertas** (plazos, licencias y recetas).
- Un **watchdog** que relanza la API si deja de responder.

Este manual se basa en los ambientes de desarrollo y QA, que ya están operativos. Los pasos deben seguirse en orden.

### 1.1 Ambientes de referencia

| Dato | DEV | QA |
|---|---|---|
| Servidor | `srv-segicepa-dev` — `segicepa-dev.utalca.cl` (192.168.22.183) | `segicepa-qa.utalca.cl` (192.168.21.202) |
| Sistema operativo | Debian GNU/Linux 12 (Bookworm) | Debian GNU/Linux 12 (Bookworm) |
| Recursos | 2 vCPU / 1,9 GB RAM | clon de DEV |
| Usuario de servicio | `segicepa` (grupo sudo) | `segicepa` (grupo sudo) |
| Servidor web | nginx de DTI (sirve también otro sitio) + servidor node en :8080 | nginx, sitio `sige-cepa`, puerto 80 |
| Base de datos | Oracle 19c, `oracle19c-dev.utalca.cl:1521`, SID `dbutal9`, esquema `UTCEPA01` | Oracle 19c, `oracle19c-test.utalca.cl:1521`, SID `dbutal9`, esquema `UTCEPA01` |
| Oracle Instant Client | 19.26 (Basic) | 19.26 (Basic) |
| Directorio de la aplicación | `/home/segicepa/sige-cepa` | `/home/segicepa/sige-cepa` y `/var/www/sige-cepa` (frontend) |
| Repositorio | GitHub (privado, Kreante) | GitHub (privado, Kreante) |
| Autenticación | Usuario y contraseña propios del sistema; SSO SAML institucional en integración | ídem |
| Acceso | Solo red UTalca o VPN | Solo red UTalca o VPN |

### 1.2 Ambiente productivo (a completar)

| Dato | Valor |
|---|---|
| Servidor | **[PENDIENTE: hostname e IP de la VM PROD]** |
| Dominio público | **[PENDIENTE: p. ej. `sige-cepa.utalca.cl`]** |
| Certificado SSL | **[PENDIENTE: certificado del dominio + intermedio + llave]** |
| Base de datos | **[PENDIENTE: host, puerto, SID y esquema Oracle PROD]** |
| Relay SMTP | **[PENDIENTE: host, puerto y cuenta para enviar las alertas]** |
| SALUTEM productivo | **[PENDIENTE: URL, código de empresa y API key de producción]** |

---

## 2. Prerrequisitos

### 2.1 Hardware y red
- VM con Debian 12 (Bookworm). Recomendado: al menos 2 vCPU, 4 GB de RAM y 20 GB libres. DEV opera con 1,9 GB de RAM, pero va justa en la compilación y en los reportes Excel.
- Acceso por VPN y SSH al servidor.
- Salida a Internet, o a los repositorios internos, para instalar paquetes de Debian y las dependencias de Python.
- Conectividad desde el servidor hacia:
    - El servidor Oracle PROD (TCP 1521).
    - La API de SALUTEM (HTTPS 443).
    - El IdP institucional `idprovider.utalca.cl` (HTTPS 443, para el SSO SAML).
    - El relay SMTP (habitualmente TCP 587).
- Servidor en zona horaria **America/Santiago**: el job de alertas corre a las 07:00 hora local.

### 2.2 Accesos necesarios
- Usuario de servicio `segicepa` con privilegios sudo.
- Credenciales del esquema Oracle PROD, solicitadas por el conducto formal (ver el documento de paso a producción).
- API key de SALUTEM para producción.
- Credenciales del relay SMTP, si se exige autenticación.
- Certificado SSL del dominio y su llave privada.
- Certificado público del IdP institucional (`idprovider.utalca.cl`) y registro del SIGE como Service Provider SAML ante DTI.
- El paquete de la versión a instalar, entregado por Kreante: código del backend, `dist/` del frontend y archivos de configuración de ejemplo.

### 2.3 Software base

| Componente | Versión requerida |
|---|---|
| Python | 3.12 (instalado con `uv`; Debian 12 trae 3.11) |
| uv | 0.4 o superior (gestor de Python y dependencias) |
| nginx | versión estable de Debian 12 |
| Oracle Instant Client | 19.26 Basic (linux x64) |
| libaio1, unzip, curl | paquetes de Debian |
| Node.js | **no requerido en el servidor**: el frontend llega ya compilado |

---

## 3. Instalación y configuración del servidor

### 3.1 Actualizar el sistema
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y nginx libaio1 unzip curl ca-certificates
sudo timedatectl set-timezone America/Santiago
```

### 3.2 Instalar uv y Python 3.12
Se ejecuta como el usuario de servicio `segicepa`, no como root:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
~/.local/bin/uv python install 3.12
~/.local/bin/uv --version
```

---

## 4. Instalación de Oracle Instant Client

**El sistema necesita el modo Thick.** El usuario Oracle institucional usa un verificador de contraseña (0x939) que el modo Thin de `python-oracledb` no sabe negociar: falla con `DPY-3015`. Por eso hace falta el Instant Client.

### 4.1 Preparar los archivos
Hay que obtener del equipo de Infraestructura, o de Oracle Technology Network, el archivo `instantclient-basic-linux.x64-19.26.0.0.0dbru.zip` y copiarlo al servidor:
```bash
scp instantclient-basic-linux.x64-19.26.0.0.0dbru.zip segicepa@SERVIDOR:/tmp/
```

### 4.2 Descomprimir
```bash
mkdir -p ~/opt
unzip /tmp/instantclient-basic-linux.x64-19.26.0.0.0dbru.zip -d ~/opt/
ls ~/opt/instantclient_19_26
```

### 4.3 Configurar el alias TNS
**`dbutal9` es un SID, no un service name.** Si se usa la forma `host:puerto/servicio`, la conexión falla con `ORA-12154`. Por eso se define un alias TNS:
```bash
mkdir -p ~/opt/tns
cat > ~/opt/tns/tnsnames.ora <<'EOF'
CEPAPROD =
  (DESCRIPTION =
    (ADDRESS = (PROTOCOL = TCP)(HOST = [PENDIENTE: host Oracle PROD])(PORT = 1521))
    (CONNECT_DATA = (SID = [PENDIENTE: SID PROD]))
  )
EOF
```

Las librerías se cargan con `LD_LIBRARY_PATH=~/opt/instantclient_19_26` y `TNS_ADMIN=~/opt/tns`. Los scripts de arranque las exportan **antes** de lanzar cada proceso; configurar `ORACLE_CLIENT_LIB_DIR` en la aplicación no basta por sí solo.

---

## 5. Obtención del código

### 5.1 Recibir el paquete de la versión
Kreante entrega un archivo `sige-cepa-<versión>.tar.gz` con esta estructura:
```
backend/        código de la API, migraciones Alembic, pyproject.toml y uv.lock
frontend-dist/  frontend ya compilado (HTML, JS y CSS estáticos)
ops/            scripts de arranque, cron y configuración nginx de referencia
wheels/         dependencias Python empaquetadas, por si el servidor no tiene salida a Internet
```

Este paquete se empaqueta con `COPYFILE_DISABLE=1 tar --no-xattrs` para que no lleve los archivos `._*` de macOS: Alembic intentaría importarlos como migraciones y fallaría con "null bytes".

**[PENDIENTE: confirmar con DTI si Infraestructura recibe el paquete o necesita acceso a un repositorio (UTalca usa Bitbucket; el código vive en GitHub).]**

### 5.2 Ubicar los archivos
```bash
mkdir -p ~/sige-cepa ~/sige-cepa/logs
tar xzf sige-cepa-<versión>.tar.gz -C ~/sige-cepa
sudo mkdir -p /var/www/sige-cepa
sudo chown segicepa:segicepa /var/www/sige-cepa
cp -a ~/sige-cepa/frontend-dist/. /var/www/sige-cepa/
```

### 5.3 Instalar dependencias del backend
```bash
cd ~/sige-cepa/backend
~/.local/bin/uv sync --frozen --no-dev
# Sin salida a Internet:
# ~/.local/bin/uv sync --frozen --no-dev --find-links ../wheels
```

---

## 6. Configuración del archivo .env

El archivo `~/sige-cepa/backend/.env` reúne toda la configuración sensible. Se crea a partir de `backend/.env.example`, con permisos `600`, y **nunca se versiona**.

```bash
cd ~/sige-cepa/backend
cp .env.example .env
chmod 600 .env
nano .env
```

### 6.1 Entorno de la aplicación

| Variable | Descripción / valor para PROD |
|---|---|
| `ENTORNO` | `prod`. Desactiva todos los atajos de desarrollo. Es el valor por defecto. |
| `FRONTEND_URL` | URL pública del sistema, p. ej. `https://[PENDIENTE: dominio]` |
| `CORS_ORIGINS` | Solo la URL pública del sistema, p. ej. `https://[PENDIENTE: dominio]` |
| `RATE_LIMIT_PER_MINUTE` | Límite de peticiones por minuto por cliente. Por defecto, `60`. |

### 6.2 Base de datos Oracle

| Variable | Descripción / valor para PROD |
|---|---|
| `DATABASE_URL` | `oracle+oracledb://<USUARIO>:<CLAVE>@CEPAPROD` (usa el alias TNS del punto 4.3) |
| `ORACLE_CLIENT_LIB_DIR` | `/home/segicepa/opt/instantclient_19_26`. Con esto se activa el modo Thick. |

### 6.3 Autenticación y tokens

| Variable | Descripción / valor para PROD |
|---|---|
| `JWT_SECRET` | Clave para firmar los tokens. Cadena aleatoria larga (`openssl rand -hex 32`), distinta en cada ambiente. |
| `JWT_ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRA_MIN` | Vigencia del token de acceso, en minutos. Por defecto, `15`. |
| `REFRESH_TOKEN_EXPIRA_MIN` | Vigencia de la sesión renovable, en minutos. Por defecto, `10080` (7 días). |
| `LOGIN_MAX_INTENTOS` | Intentos fallidos antes de bloquear la cuenta. Por defecto, `5`. |
| `LOGIN_BLOQUEO_MINUTOS` | Duración del bloqueo, en minutos. Por defecto, `15`. |

### 6.4 SSO institucional (SAML 2.0)

| Variable | Descripción / valor para PROD |
|---|---|
| `SAML_SP_ENTITY_ID` | `https://[PENDIENTE: dominio]/api/v1/auth/saml/metadata`. Es también la URL donde DTI descarga la metadata del SP. |
| `SAML_SP_ACS_URL` | `https://[PENDIENTE: dominio]/api/v1/auth/saml/acs`. Debe coincidir con lo que registre DTI en el IdP. |
| `SAML_IDP_CERT` | Certificado público del IdP `idprovider.utalca.cl`. Si queda vacío, el SSO no autentica a nadie (falla cerrado). |
| `SSO_HUEMUL_MODO` | `deshabilitado`. El wrapper huemul no se puede usar de forma segura porque su ticket es constante. |

### 6.5 Correo de alertas (SMTP)

| Variable | Descripción / valor para PROD |
|---|---|
| `SMTP_HOST` | **[PENDIENTE]** Si queda vacío, no se envían correos; las alertas siguen apareciendo dentro del sistema. |
| `SMTP_PORT` | Habitualmente `587` |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | **[PENDIENTE]**, si el relay exige autenticación |
| `SMTP_USE_TLS` | `true` |
| `SMTP_FROM_ADDR` | Remitente, p. ej. `cepa-alertas@utalca.cl` **[PENDIENTE: confirmar cuenta]** |

### 6.6 Integración SALUTEM (solo lectura)

| Variable | Descripción / valor para PROD |
|---|---|
| `SALUTEM_BASE_URL` | **[PENDIENTE: URL de producción]**. En QA es `https://qa.salutem.cl/api/integraciones/salutem`. |
| `SALUTEM_EMPRESA` | **[PENDIENTE: código de empresa en PROD]** |
| `SALUTEM_API_KEY` | **[PENDIENTE: API key de PROD]** |
| `SALUTEM_TIMEOUT_S` | `30` |
| `SALUTEM_SYNC_HABILITADO` | `true`. Con `false`, los cron quedan instalados pero no salen a la red. |
| `SALUTEM_SYNC_LLAMADAS_POR_SEG` | `2` |
| `SALUTEM_SYNC_LOG` | `/home/segicepa/sige-cepa/logs/salutem-sync.log` |
| `SALUTEM_SYNC_PERSONAS_PERMITIDAS` | Vacío en PROD (todas las personas). En QA se limita a pacientes de prueba. |
| `CITAS_SALUTEM_DESDE` | Fecha (AAAA-MM-DD) desde la que se traen las citas, p. ej. `2026-01-01` **[PENDIENTE: confirmar con el CEPA]** |
| `SALUTEM_BORRADORES_DESDE` | Fecha desde la que se crean pacientes borrador desde SALUTEM **[PENDIENTE: confirmar con el CEPA]** |
| `SALUTEM_ESPECIALIDADES_CONTROL` / `SALUTEM_ESPECIALIDADES_ALERTA` / `CITAS_ESPECIALIDADES_REPORTES` | Se dejan los valores por defecto, salvo que el CEPA pida otra cosa. |

### 6.7 Procesos programados

| Variable | Descripción / valor para PROD |
|---|---|
| `ALERTAS_JOB_LOG` | `/home/segicepa/sige-cepa/logs/alertas-job.log` |
| `IMED_ENABLED` | `false` (la integración IMED no está activa) |

---

## 7. Configuración de nginx

### 7.1 Certificados SSL
```bash
sudo mkdir -p /etc/nginx/ssl && sudo chmod 700 /etc/nginx/ssl
sudo mv dominio.crt intermediate.crt dominio.key /etc/nginx/ssl/
sudo sh -c 'cat /etc/nginx/ssl/dominio.crt /etc/nginx/ssl/intermediate.crt > /etc/nginx/ssl/dominio.fullchain.crt'
sudo chmod 600 /etc/nginx/ssl/*.key && sudo chmod 644 /etc/nginx/ssl/*.crt
sudo chown root:root /etc/nginx/ssl/*
```

### 7.2 Sitio de nginx
Archivo `/etc/nginx/sites-available/sige-cepa`:
```nginx
server {
    listen 80;
    server_name [DOMINIO];
    return 301 https://[DOMINIO]$request_uri;
}

server {
    listen 443 ssl http2;
    server_name [DOMINIO];

    ssl_certificate     /etc/nginx/ssl/dominio.fullchain.crt;
    ssl_certificate_key /etc/nginx/ssl/dominio.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_session_cache shared:SSL:10m;

    root /var/www/sige-cepa;
    index index.html;

    # Lectura de PDF de licencias (hasta 10 MB)
    client_max_body_size 12m;

    access_log /var/log/nginx/sige-cepa.access.log;
    error_log  /var/log/nginx/sige-cepa.error.log;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    location = /health {
        proxy_pass http://127.0.0.1:8000;
    }

    # Aplicación de una sola página: toda ruta desconocida devuelve index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    location ~ /\.(?!well-known).* {
        deny all;
    }
}
```

### 7.3 Activar y verificar
```bash
sudo ln -s /etc/nginx/sites-available/sige-cepa /etc/nginx/sites-enabled/sige-cepa
sudo nginx -t
sudo systemctl reload nginx
```

El frontend se compila con `VITE_API_BASE_URL` vacío. Así llama a la API por la ruta relativa `/api/`, y el mismo build sirve para cualquier servidor.

---

## 8. Base de datos y arranque de la aplicación

### 8.1 Crear o actualizar el esquema
Las migraciones crean el esquema completo: 48 tablas, más los datos iniciales que necesita el sistema (tramos GAF, plazos y festivos de las alertas, catálogos de fármacos). Los convenios no se cargan aquí: son un espejo del catálogo de SALUTEM y llegan con la sincronización.
```bash
cd ~/sige-cepa/backend
export LD_LIBRARY_PATH=$HOME/opt/instantclient_19_26
export TNS_ADMIN=$HOME/opt/tns
.venv/bin/alembic upgrade head
.venv/bin/alembic current      # debe mostrar 1580 (head)
```

### 8.2 Crear el primer usuario administrador
```bash
.venv/bin/python -m app.scripts.seed_admin --username <usuario> --password '<clave temporal>' --nombre '<Nombre>'
```
Después, ese usuario crea el resto de las cuentas desde la propia aplicación.

### 8.3 Servicio de la API (systemd)
Archivo `/etc/systemd/system/sige-cepa-api.service`:
```ini
[Unit]
Description=SIGE-CEPA API (uvicorn)
After=network-online.target

[Service]
User=segicepa
WorkingDirectory=/home/segicepa/sige-cepa/backend
Environment=LD_LIBRARY_PATH=/home/segicepa/opt/instantclient_19_26
Environment=TNS_ADMIN=/home/segicepa/opt/tns
ExecStart=/home/segicepa/sige-cepa/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sige-cepa-api
```
En DEV y QA, la API se arranca con `~/sige-cepa/run-api.sh` desde `@reboot` en el crontab y la vigila un watchdog cada 5 minutos. En PROD se recomienda systemd, que reinicia el servicio solo; con eso el watchdog deja de hacer falta.

### 8.4 Procesos programados (crontab del usuario segicepa)
```bash
cp ~/sige-cepa/ops/vm/run-*.sh ~/sige-cepa/ && chmod +x ~/sige-cepa/run-*.sh
crontab -e
```
```
# Sincronización SALUTEM (solo lectura)
*/5 * * * * $HOME/sige-cepa/run-salutem-sync.sh caliente
7 * * * *   $HOME/sige-cepa/run-salutem-sync.sh tibia
32 13 * * * $HOME/sige-cepa/run-salutem-sync.sh fria
# Alertas diarias, lunes a viernes 07:00
0 7 * * 1-5 $HOME/sige-cepa/run-alertas.sh
```
Cada script exporta el entorno Oracle, usa `flock` para no superponer ejecuciones y escribe su log en `~/sige-cepa/logs/`. La sincronización fría corre a las 13:32 en QA porque SALUTEM QA no responde de noche; en PROD, el horario se ajusta según la disponibilidad de SALUTEM productivo **[PENDIENTE]**.

### 8.5 Carga inicial desde SALUTEM
Solo se ejecuta una vez, después de configurar SALUTEM en el `.env`:
```bash
~/sige-cepa/run-salutem-sync.sh backfill
~/sige-cepa/run-salutem-sync.sh vincular --todo
~/sige-cepa/run-salutem-sync.sh estado
```

---

## 9. Verificación de la instalación

### 9.1 Comandos de verificación
```bash
systemctl status nginx
systemctl status sige-cepa-api
curl -s http://127.0.0.1:8000/health          # {"status":"ok"} o similar, HTTP 200
curl -I https://[DOMINIO]                      # HTTP 200
curl -s https://[DOMINIO]/health               # HTTP 200 a través de nginx
cd ~/sige-cepa/backend && .venv/bin/alembic current
~/sige-cepa/run-salutem-sync.sh estado
crontab -l
tail -f /var/log/nginx/sige-cepa.error.log
tail -f ~/sige-cepa/logs/salutem-sync.log ~/sige-cepa/logs/alertas-job.log
```

### 9.2 Checklist final

| Ítem | Estado esperado |
|---|---|
| Python 3.12 | `uv python list` muestra 3.12 instalado |
| Instant Client | `~/opt/instantclient_19_26` existe y `tnsnames.ora` tiene el alias PROD |
| Archivo .env | Existe, permisos 600, `ENTORNO=prod` |
| Migraciones | `alembic current` muestra `1580 (head)` |
| API | `systemctl status sige-cepa-api` en `active (running)` y `/health` responde 200 |
| nginx | `nginx -t` OK, sitio `sige-cepa` habilitado |
| HTTPS | El dominio responde por HTTPS con certificado válido y HTTP redirige a HTTPS |
| Puertos | Solo 80 y 443 expuestos; 8000 escucha solo en 127.0.0.1 |
| Inicio de sesión | El usuario administrador entra y ve el dashboard |
| SSO SAML | El login institucional vuelve al sistema autenticado |
| SALUTEM | `run-salutem-sync.sh estado` muestra ciclos OK |
| Alertas | El job de las 07:00 deja registro en `alertas-job.log`; llega un correo de prueba |
| Logs | Sin errores críticos en nginx, la API ni los procesos programados |
