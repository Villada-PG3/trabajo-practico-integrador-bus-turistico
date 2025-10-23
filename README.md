# TP Integrador – Bus Turístico (Django)

Este proyecto es una aplicación de bus turístico desarrollada en Django, que permite a los usuarios explorar distintos recorridos turísticos en Buenos Aires, asi pudiendo ver los distintos tipos asignados con colores. Cada uno tiene sus distintas paradas, las cuales pueden ser compartidas entre los distintos recorridos, y dentro de cada una se encuentran los atractivos con sus calificaciones.

---

## Integrantes — Grupo 7
- **Tomás Nuñez**
- **Matías Carrera**
- **Valentino Olmedo**
- **Lautaro Benavidez**

---

## Índice
1. [Descripción](#descripción)
2. [Requisitos Previos](#requisitos-previos)
3. [Instalación](#instalación)
   - [venv + pip (recomendada)](#venv--pip)
4. [Configuración de Base de Datos](#configuración-de-base-de-datos)
   - [SQLite (desarrollo)](#sqlite-desarrollo)
5. [Migraciones, Datos de Ejemplo y Superusuario](#migraciones-datos-de-ejemplo-y-superusuario)
6. [Ejecutar la Aplicación](#ejecutar-la-aplicación)
7. [Solución de Problemas Frecuentes](#solución-de-problemas-frecuentes)

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
- **Windows/macOS/Linux**

---

## Instalación

### venv + pip
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

---

## Configuración de Base de Datos

### SQLite (desarrollo)
No requiere pasos extra. Django usará un archivo `db.sqlite3` en la raíz (o el path definido en `settings.py`).

> Recomendado para empezar rápido.

---

## Migraciones, Datos de Ejemplo y Superusuario
```bash
# Crear/estructurar tablas
python manage.py migrate

# Hacer un load de los datos del json:
python manage.py loaddata datos_iniciales.json

# Crear administrador para /admin
python manage.py createsuperuser
```
---

## Ejecutar la Aplicación
```bash
python manage.py runserver
```
- App: http://127.0.0.1:8000  
- Admin: http://127.0.0.1:8000/admin/dashboard/

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
