# Trabajo Práctico Integrador – Bus Turístico (Django)
Guía rápida para **instalar**, **configurar** y **ejecutar** el proyecto desde cero.

> Esta guía asume cero experiencia previa con Django/Python. Vas a crear el entorno virtual, instalar dependencias, preparar la base de datos y levantar el servidor.

---

## Requisitos
- **Python 3.10+**
- **pip** (gestor de paquetes de Python)
- **Git**
- **SQLite** (viene por defecto con Python)  
  > Para producción se recomienda **PostgreSQL 13+**.

---

## 1) Clonar el repositorio
```bash
git clone https://github.com/Villada-PG3/trabajo-practico-integrador-bus-turistico.git
cd trabajo-practico-integrador-bus-turistico
```

---

## 2) Crear y activar entorno virtual

**Windows (PowerShell):**
```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
```

**macOS / Linux (bash/zsh):**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

> Para salir del entorno virtual luego: `deactivate`

---

## 3) Instalar dependencias
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 4) Variables de entorno (`.env`)
En la **raíz del proyecto** (misma carpeta que `manage.py`), creá un archivo llamado **`.env`** con al menos:

```env
# Seguridad
SECRET_KEY=poné_una_clave_larga_y_unica
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Base de datos (opción A: SQLite por defecto)
# No hace falta configurar nada extra para SQLite

# Base de datos (opción B: PostgreSQL - producción)
# DATABASE_URL=postgres://usuario:password@localhost:5432/bus_turistico

# Localización (opcional)
TIME_ZONE=America/Argentina/Cordoba
LANGUAGE_CODE=es-ar

# Servicios externos (opcional, si usan ruteo OSRM)
# OSRM_BASE_URL=http://127.0.0.1:5000
```

> Sugerencia: agregá al repo un **`.env.example`** con las claves vacías (no subas `.env` reales).

---

## 5) Configurar la base de datos

### Opción A — **SQLite (desarrollo, predeterminado)**
No requiere pasos extra. Django usará un archivo `db.sqlite3` en la raíz (o lo definido en `settings.py`).

### Opción B — **PostgreSQL (recomendado en producción)**
1. Crear DB y usuario:
   ```sql
   CREATE DATABASE bus_turistico;
   CREATE USER bus_user WITH PASSWORD 'tu_password';
   GRANT ALL PRIVILEGES ON DATABASE bus_turistico TO bus_user;
   ```
2. En `.env`, definir `DATABASE_URL`:
   ```env
   DATABASE_URL=postgres://bus_user:tu_password@localhost:5432/bus_turistico
   ```
3. Instalar el conector si hiciera falta:
   ```bash
   pip install psycopg2-binary
   ```

---

## 6) Migraciones y superusuario
Aplicá el esquema de la base de datos y creá un admin:

```bash
python manage.py migrate
python manage.py createsuperuser
```

> Seguí las instrucciones en consola para usuario/contraseña del panel de administración.

---

## 7) Ejecutar la aplicación (desarrollo)
```bash
python manage.py runserver
```
Abrí el navegador en **http://127.0.0.1:8000**  
Panel de administración: **http://127.0.0.1:8000/admin** (usa el superusuario creado).

---

## 8) Archivos estáticos y media
- **Static** = CSS/JS/imagenes del sitio (no cambian por usuario).  
- **Media** = archivos **subidos por usuarios** (fotos, PDFs, etc.).

Asegurate de tener en `settings.py`:

```python
STATIC_URL = "/static/"
# (opcional) STATICFILES_DIRS = [BASE_DIR / "static"]  # si usás carpeta global
# En producción:
# STATIC_ROOT = BASE_DIR / "staticfiles"  # destino de collectstatic

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

En producción, recordá ejecutar:
```bash
python manage.py collectstatic
```

> **Importante**: no versionar `media/` en Git (agregalo a `.gitignore`).

---

## 9) Despliegue (resumen)
- `DEBUG=False`
- `ALLOWED_HOSTS=tu-dominio.com`
- Base de datos real (PostgreSQL) y `DATABASE_URL` configurada
- Servir estáticos desde `STATIC_ROOT` (tras `collectstatic`)
- Usar **gunicorn/uvicorn** detrás de **Nginx/Apache**
- Rotar **SECRET_KEY** si alguna vez se publicó por error

---

## 10) Solución de problemas frecuentes
- **`ModuleNotFoundError`** → el entorno virtual no está activado; activalo y reinstalá dependencias.
- **`DisallowedHost`** en producción → falta el dominio en `ALLOWED_HOSTS`.
- **CSS/JS no cargan** en producción → faltó `collectstatic` o el servidor no apunta a `STATIC_ROOT`.
- **`psycopg2` no compila** → usá `psycopg2-binary` en desarrollo.

---

## 11) Estructura de referencia (simplificada)
```
.
├─ manage.py
├─ config/ o <nombre_proyecto>/     # settings/urls/asgi/wsgi
├─ apps/ (ej. buses, choferes, recorridos)
│  ├─ models.py  # ORM (tablas)
│  ├─ views.py   # lógica de vistas
│  ├─ urls.py    # rutas de la app
│  ├─ templates/<app>/*.html
│  └─ static/<app>/* (css/js/img)
├─ templates/   # (opcional) globales
├─ static/      # (opcional) globales
├─ media/       # (no versionar; subidas de usuarios)
├─ requirements.txt
└─ .env         # variables locales (no versionar)
```

---

## 12) Contribución
1. Abrí un **issue** describiendo el problema o la mejora.
2. Creá una rama a partir de `main`.
3. Enviá un **Pull Request** con cambios pequeños y bien explicados.

---

**¡Listo!** Con esto deberías poder levantar el proyecto localmente y preparar un despliegue básico.
