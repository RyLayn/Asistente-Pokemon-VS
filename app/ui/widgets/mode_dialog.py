"""Diálogo de selección del modo de combate al iniciar."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_NAME, MODE_DOUBLES, MODE_SINGLES


class ModeDialog(QDialog):
    """Pregunta al usuario el modo de combate (individual o dobles)."""

    def __init__(self, current: str = MODE_SINGLES, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — Modo de combate")
        self.setModal(True)
        self.selected = current
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("¿Cómo vas a combatir?")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Elige el formato. Podrás cambiarlo luego desde la barra superior.")
        subtitle.setObjectName("Subtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        cards = QHBoxLayout()
        cards.setSpacing(16)
        cards.addWidget(self._mode_card(
            "⚔️  Individual",
            "Equipo de 6 · eliges 3\n1 Pokémon activo por lado",
            MODE_SINGLES,
        ))
        cards.addWidget(self._mode_card(
            "⚔️⚔️  Dobles",
            "Equipo de 6 · eliges 4\n2 Pokémon activos por lado",
            MODE_DOUBLES,
        ))
        layout.addLayout(cards)

    def _mode_card(self, title: str, desc: str, mode: str) -> QPushButton:
        button = QPushButton(f"{title}\n\n{desc}")
        button.setObjectName("ModeCard")
        button.setMinimumSize(220, 150)
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(lambda: self._choose(mode))
        return button

    def _choose(self, mode: str) -> None:
        self.selected = mode
        self.accept()
