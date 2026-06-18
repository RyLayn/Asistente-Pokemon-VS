"""Punto de entrada de Pokémon Champions Assistant.

Inicializa el registro de eventos, la base de datos local, los servicios de la
aplicación y la ventana principal de PySide6.

Creado por RyLayn — https://github.com/RyLayn — © 2026 RyLayn.
"""

from __future__ import annotations

import sys

from app.config import APP_NAME, APP_VERSION
from app.utils.logger import get_logger, setup_logging


def main() -> int:
    """Arranca la aplicación de escritorio y devuelve el código de salida."""
    setup_logging()
    logger = get_logger(__name__)
    logger.info("Iniciando %s v%s", APP_NAME, APP_VERSION)

    # Importaciones diferidas: la capa de datos no depende de Qt.
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from app.services.database_service import DatabaseService
    from app.services.sprite_service import SpriteService
    from app.services.team_service import TeamService
    from app.ui.main_window import MainWindow
    from app.ui.themes.theme_manager import ThemeManager
    from app.utils.paths import icon_path

    # Servicios (independientes de la interfaz). La carga ocurre en el __init__.
    db = DatabaseService()
    logger.info("Pokédex cargada: %d Pokémon", len(db.all_pokemon_names()))

    settings = ThemeManager.load_settings()
    sprite_service = SpriteService(enable_download=settings.download_sprites)
    team_service = TeamService(db)

    # Aplicación Qt.
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    if icon_path().exists():
        app.setWindowIcon(QIcon(str(icon_path())))

    theme_manager = ThemeManager(app, settings)
    theme_manager.apply()

    # Selección de modo de combate al iniciar.
    from app.ui.widgets.mode_dialog import ModeDialog

    dialog = ModeDialog(current=settings.mode)
    dialog.exec()
    mode = dialog.selected
    settings.mode = mode
    theme_manager.save_settings()

    window = MainWindow(db, team_service, sprite_service, theme_manager, mode=mode)
    window.show()

    exit_code = app.exec()
    theme_manager.save_settings()
    logger.info("Aplicación finalizada (código %d)", exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
