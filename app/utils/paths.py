"""Resolución centralizada de rutas de la aplicación.

Funciona tanto en ejecución normal (``python main.py``) como dentro de un
ejecutable empaquetado con PyInstaller (modo ``--onefile`` o ``--onedir``).

Los *recursos de solo lectura* (Pokédex completa, sprites, temas) viajan
**dentro** del ejecutable. Los pocos datos *escribibles* (ajustes, equipos
guardados, registro) se guardan en la carpeta de datos del usuario del sistema
operativo (p. ej. ``%LOCALAPPDATA%`` en Windows), de modo que el ejecutable no
crea ninguna carpeta de datos a su lado.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from app.config import APP_NAME


def is_frozen() -> bool:
    """Indica si la aplicación se ejecuta empaquetada con PyInstaller."""
    return getattr(sys, "frozen", False)


def resource_root() -> Path:
    """Directorio raíz de *recursos de solo lectura* incluidos en el bundle.

    En PyInstaller los datos añadidos se extraen en ``sys._MEIPASS``.
    En desarrollo apuntamos a la raíz del proyecto.
    """
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[2]


def _slug() -> str:
    return APP_NAME.replace(" ", "")


def user_data_root() -> Path:
    """Carpeta de datos del usuario del sistema operativo.

    Toda la información escribible vive aquí cuando la app está compilada, así
    el ejecutable queda limpio (no genera carpetas de datos a su lado).
    """
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return root / _slug()


def app_root() -> Path:
    """Directorio raíz *escribible*.

    Compilado: carpeta de datos del usuario (no junto al exe).
    Desarrollo: raíz del proyecto.
    """
    if is_frozen():
        return user_data_root()
    return Path(__file__).resolve().parents[2]


# --- Carpetas de datos (escribibles) ---------------------------------------

def data_dir() -> Path:
    path = app_root() / "app" / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_dir() -> Path:
    path = data_dir() / "database"
    path.mkdir(parents=True, exist_ok=True)
    return path


def seed_dir() -> Path:
    """Datos semilla de solo lectura embebidos en el bundle."""
    return resource_root() / "app" / "data" / "database" / "seed"


def images_dir() -> Path:
    path = data_dir() / "images" / "pokemon"
    path.mkdir(parents=True, exist_ok=True)
    return path


def seed_images_dir() -> Path:
    """Sprites de solo lectura embebidos en el bundle (semilla)."""
    return resource_root() / "app" / "data" / "images" / "seed"


def cache_dir() -> Path:
    path = data_dir() / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def teams_dir() -> Path:
    path = data_dir() / "teams"
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    return database_dir() / "pokemon.db"


def themes_dir() -> Path:
    return resource_root() / "app" / "ui" / "themes"


def assets_dir() -> Path:
    return resource_root() / "assets"


def icon_path() -> Path:
    return assets_dir() / "icon.ico"
