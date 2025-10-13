# TP Integrador – Bus Turístico (Django)

Este proyecto es una aplicación de bus turístico desarrollada en Django, que permite a los usuarios explorar distintos recorridos turísticos en Buenos Aires, asi pudiendo ver los distintos tipos asignados con colores. Cada uno tiene sus distintas paradas, las cuales pueden ser compartidas entre los distintos recorridos, y dentro de cada una se encuentran los atractivos con sus calificaciones.
---

## Integrantes — Grupo 2
- **Tomás Nuñez** (con ñ)
- **Matías Carrera**
- **Valentín Olmedo**
- **Lautaro Benavidez**

---

## Índice
1. [Descripción](#descripción)
2. [Requisitos Previos](#requisitos-previos)
3. [Instalación](#instalación)
   - [Opción A — venv + pip (recomendada)](#opción-a--venv--pip-recomendada)
   - [Opción B — pipenv (alternativa)](#opción-b--pipenv-alternativa)
4. [Configuración de Base de Datos](#configuración-de-base-de-datos)
   - [SQLite (desarrollo)](#sqlite-desarrollo)
   - [MySQL (alternativa)](#mysql-alternativa)
5. [Migraciones, Datos de Ejemplo y Superusuario](#migraciones-datos-de-ejemplo-y-superusuario)
6. [Ejecutar la Aplicación](#ejecutar-la-aplicación)
7. [Archivos estáticos y media](#archivos-estáticos-y-media)
8. [Solución de Problemas Frecuentes](#solución-de-problemas-frecuentes)
9. [Estructura Sugerida](#estructura-sugerida)
10. [Contribución](#contribución)

---

## Descripción
Proyecto educativo que modela:
- **Recorridos** turísticos (identificados con colores).
- **Paradas** compartidas entre recorridos.
- **Atractivos** dentro de cada parada, con sus **calificaciones**.

---

## Requisitos Previos
- **Python 3.10+**
- **Git**
- **SQLite** (incluido por defecto con Python)  
  > Alternativa BD: **MySQL** (para quienes quieran practicar con un motor externo).
- **Windows/macOS/Linux**

---

## Instalación

### Opción A — venv + pip (recomendada)
```bash
# 1) Clonar
git clone https://github.com/Villada-PG3/trabajo-practico-integrador-bus-turistico.git
cd trabajo-practico-integrador-bus-turistico

# 2) Crear entorno virtual
# Windows (PowerShell)
python -m venv .venv
. .\.venv\Scripts\Activate.ps1

# macOS / Linux
# python3 -m venv .venv
# source .venv/bin/activate

# 3) Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
```

### Opción B — pipenv (alternativa)
```bash
# 1) Clonar
git clone https://github.com/Villada-PG3/trabajo-practico-integrador-bus-turistico.git
cd trabajo-practico-integrador-bus-turistico

# 2) Instalar y activar entorno
pip install --user pipenv
pipenv install
pipenv shell
```

---

## Configuración de Base de Datos

### SQLite (desarrollo)
No requiere pasos extra. Django usará un archivo `db.sqlite3` en la raíz (o el path definido en `settings.py`).

> Recomendado para empezar rápido.

### MySQL (alternativa)
> Útil si tu docente pide MySQL. **No publiques contraseñas reales** en el repositorio.

1. **Entrar a MySQL como root**:
   ```bash
   mysql -u root -p
   ```

2. **Crear base y usuario** (cambiá usuario/contraseña a gusto):
   ```sql
   CREATE DATABASE busturistico CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'bustu_user'@'localhost' IDENTIFIED BY 'cambia_esta_password';
   GRANT ALL PRIVILEGES ON busturistico.* TO 'bustu_user'@'localhost';
   FLUSH PRIVILEGES;
   EXIT;
   ```

3. **Configurar Django**. Recomendado vía variables de entorno (`.env` en la raíz, mismo nivel que `manage.py`):
   ```env
   # .env (ejemplo)
   DEBUG=True
   SECRET_KEY=cambia_esta_clave_unica_y_larga
   ALLOWED_HOSTS=localhost,127.0.0.1

   # MySQL
   DB_ENGINE=django.db.backends.mysql
   DB_NAME=busturistico
   DB_USER=bustu_user
   DB_PASSWORD=cambia_esta_password
   DB_HOST=localhost
   DB_PORT=3306
   ```

   > Si tu proyecto no usa `.env`, podés editar `settings.py` manualmente en el bloque `DATABASES`:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.mysql',
           'NAME': 'busturistico',
           'USER': 'bustu_user',
           'PASSWORD': 'cambia_esta_password',
           'HOST': 'localhost',
           'PORT': '3306',
       }
   }
   ```

> **Paquete de MySQL**: si no está en `requirements.txt`, instalá `mysqlclient` o `PyMySQL`.
> ```bash
> pip install mysqlclient  # (Windows puede requerir compiladores) 
> # o
> pip install PyMySQL
> ```

---

## Migraciones, Datos de Ejemplo y Superusuario
```bash
# Crear/estructurar tablas
python manage.py migrate

# (Opcional) Cargar datos de ejemplo si existe un fixture db.json
# python manage.py loaddata db.json

# Crear administrador para /admin
python manage.py createsuperuser
```

> Si el docente entrega credenciales de prueba, **no** las subas al repo público. Usalas localmente.

---

## Ejecutar la Aplicación
```bash
python manage.py runserver
```
- App: http://127.0.0.1:8000  
- Admin: http://127.0.0.1:8000/admin

---

## Archivos estáticos y media
- **Static** = CSS/JS/imagenes del sitio (no cambian por usuario).
- **Media** = archivos **subidos por usuarios** (fotos, PDFs). **No** versionar en Git.

En `settings.py` verificá (o agregá):
```python
STATIC_URL = "/static/"
# (opcional) STATICFILES_DIRS = [BASE_DIR / "static"]  # si usás carpeta global
# En despliegue:
# STATIC_ROOT = BASE_DIR / "staticfiles"  # destino de collectstatic

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

Para producción:
```bash
python manage.py collectstatic
```

---

## Solución de Problemas Frecuentes
- **`ModuleNotFoundError`** → no activaste el entorno virtual. Activá y reinstalá dependencias.
- **`DisallowedHost`** (prod) → falta tu dominio en `ALLOWED_HOSTS`.
- **CSS/JS no cargan** (prod) → falta `collectstatic` o el servidor no apunta a `STATIC_ROOT`.
- **Error con MySQL** → revisá usuario/clave/puerto; probá `PyMySQL` si `mysqlclient` falla.
- **Permisos o “posesión dudosa” (Linux/montajes)** →
  ```bash
  git config --global --add safe.directory /ruta/a/tu/repo
  ```

---

## Estructura Sugerida
```
.
├─ manage.py
├─ <nombre_proyecto>/        # settings/urls/asgi/wsgi
├─ apps/ (buses, choferes, recorridos, etc.)
│  ├─ models.py
│  ├─ views.py
│  ├─ urls.py
│  ├─ templates/<app>/*.html
│  └─ static/<app>/* (css/js/img)
├─ templates/                # (opcional) globales
├─ static/                   # (opcional) globales
├─ media/                    # (no versionar; subidas)
├─ requirements.txt
└─ .env                      # variables locales (no versionar)
```

---

## Contribución
1. Abrí un **issue** con detalle (pasos para reproducir, esperado vs. obtenido).
2. Creá una rama desde `main` y hacé cambios pequeños, con mensajes claros.
3. Enviá un **Pull Request**.

---

> **Nota de seguridad:** No publiques usuarios/contraseñas reales ni claves (`SECRET_KEY`, tokens) en el repositorio. Si alguna vez se subieron, **rotalas** y eliminá del historial o generá un snapshot limpio.
