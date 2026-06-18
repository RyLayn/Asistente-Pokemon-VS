"""Etiqueta de sprite reutilizable.

Muestra el sprite de un Pokémon (escalado con suavizado nulo para conservar el
aspecto pixel art de 8 bits). Si no hay sprite disponible offline, dibuja un
marcador de posición discreto con la inicial del Pokémon.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from app.services.database_service import DatabaseService
from app.services.sprite_service import SpriteService


class SpriteLabel(QLabel):
    """Muestra el sprite de una especie, con caché y marcador de posición."""

    def __init__(
        self,
        db: DatabaseService,
        sprites: SpriteService,
        size: int = 96,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._sprites = sprites
        self._size = size
        self._species = ""
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)
        self.setScaledContents(False)
        self._show_placeholder("")

    def set_species(self, species: str) -> None:
        self._species = species or ""
        if not self._species:
            self._show_placeholder("")
            return
        mon = self._db.get_pokemon(self._species)
        if mon is None:
            self._show_placeholder(self._species[:1].upper())
            return
        path = self._sprites.get_sprite(mon)
        if path is None:
            self._show_placeholder(self._species[:1].upper())
            return
        pix = QPixmap(str(path))
        if pix.isNull():
            self._show_placeholder(self._species[:1].upper())
            return
        # Escalado nítido (pixel art): sin interpolación suave.
        scaled = pix.scaled(
            self._size, self._size,
            Qt.KeepAspectRatio, Qt.FastTransformation,
        )
        self.setPixmap(scaled)

    def _show_placeholder(self, letter: str) -> None:
        pix = QPixmap(self._size, self._size)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing, True)
        r = self._size - 10
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(120, 120, 130, 40))
        painter.drawEllipse(5, 5, r, r)
        if letter:
            painter.setPen(QColor(150, 150, 160))
            font = QFont()
            font.setPixelSize(int(self._size * 0.42))
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(pix.rect(), Qt.AlignCenter, letter)
        painter.end()
        self.setPixmap(pix)


def make_icon_provider(db, sprites):
    """Devuelve una función nombre->QIcon (sprite pequeño) con caché, para los
    cuadros de búsqueda de Pokémon."""
    from PySide6.QtGui import QIcon
    cache: dict[str, object] = {}

    def provider(name: str):
        mon = db.get_pokemon(name)
        if mon is None:
            return None
        key = mon.sprite_key
        if key in cache:
            return cache[key]
        path = sprites.resolve_existing(mon)
        icon = QIcon(str(path)) if path else None
        cache[key] = icon
        return icon

    return provider
