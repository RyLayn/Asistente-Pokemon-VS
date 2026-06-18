"""Gestión de temas (oscuro/claro) y persistencia de ajustes.

Carga las hojas de estilo QSS desde disco y permite cambiar de tema en
tiempo de ejecución. Los ajustes del usuario se guardan en un pequeño JSON
junto a los datos escribibles de la aplicación.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from app.config import Settings
from app.utils.logger import get_logger
from app.utils.paths import data_dir, themes_dir

if TYPE_CHECKING:  # pragma: no cover
    from PySide6.QtWidgets import QApplication

logger = get_logger(__name__)

_SETTINGS_FILE = "settings.json"
_THEMES = ("dark", "light")


class ThemeManager:
    """Aplica y alterna temas, y persiste la preferencia del usuario."""

    def __init__(self, app: "QApplication", settings: Settings | None = None) -> None:
        self.app = app
        self.settings = settings or self.load_settings()
        self._cache: dict[str, str] = {}

    # --- Carga de QSS ------------------------------------------------------

    def _qss_path(self, theme: str) -> Path:
        return themes_dir() / f"{theme}.qss"

    def _read_qss(self, theme: str) -> str:
        if theme in self._cache:
            return self._cache[theme]
        path = self._qss_path(theme)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.error("No se pudo leer el tema %s: %s", theme, exc)
            text = ""
        self._cache[theme] = text
        return text

    # --- Aplicación --------------------------------------------------------

    def apply(self, theme: str | None = None) -> None:
        """Aplica el tema indicado (o el de los ajustes) a la aplicación."""
        theme = theme or self.settings.theme
        if theme not in _THEMES:
            theme = "dark"
        self.app.setStyleSheet(self._read_qss(theme))
        self.settings.theme = theme
        logger.info("Tema aplicado: %s", theme)

    def toggle(self) -> str:
        """Alterna entre oscuro y claro, lo aplica y lo persiste."""
        new_theme = "light" if self.settings.theme == "dark" else "dark"
        self.apply(new_theme)
        self.save_settings()
        return new_theme

    # --- Persistencia de ajustes ------------------------------------------

    @staticmethod
    def _settings_path() -> Path:
        return data_dir() / _SETTINGS_FILE

    @classmethod
    def load_settings(cls) -> Settings:
        path = cls._settings_path()
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return Settings.from_dict(data)
            except (OSError, ValueError) as exc:
                logger.warning("Ajustes ilegibles, se usan valores por defecto: %s", exc)
        return Settings()

    def save_settings(self) -> None:
        path = self._settings_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(self.settings.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.error("No se pudieron guardar los ajustes: %s", exc)
