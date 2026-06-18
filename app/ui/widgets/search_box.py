"""Cuadro de búsqueda predictiva reutilizable.

Combina un ``QLineEdit`` con un popup de sugerencias alimentado por
``SearchService`` (RapidFuzz). Opcionalmente muestra un **sprite pequeño** junto
a cada sugerencia (útil para identificar un Pokémon sin saber su nombre).
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QCompleter, QLineEdit

from app.services.search_service import SearchService


class SearchBox(QLineEdit):
    """Campo de texto con autocompletado difuso y sprites opcionales."""

    itemChosen = Signal(str)

    def __init__(
        self,
        search_service: SearchService,
        placeholder: str = "Buscar…",
        limit: int = 8,
        icon_provider: Optional[Callable[[str], Optional[QIcon]]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._search = search_service
        self._limit = limit
        self._icon_provider = icon_provider
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)

        self._model = QStandardItemModel(self)
        self._completer = QCompleter(self._model, self)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchContains)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        if icon_provider is not None:
            popup = self._completer.popup()
            popup.setIconSize(QSize(32, 32))
        self.setCompleter(self._completer)

        self.textEdited.connect(self._on_text_edited)
        self._completer.activated.connect(self._on_activated)
        self.returnPressed.connect(self._on_return)

    # --- Lógica de sugerencias --------------------------------------------

    def _on_text_edited(self, text: str) -> None:
        text = text.strip()
        self._model.clear()
        if not text:
            return
        for name in self._search.search(text, limit=self._limit):
            item = QStandardItem(name)
            item.setEditable(False)
            if self._icon_provider is not None:
                icon = self._icon_provider(name)
                if icon is not None:
                    item.setIcon(icon)
            self._model.appendRow(item)
        self._completer.complete()

    def _on_activated(self, text: str) -> None:
        self.setText(text)
        self.itemChosen.emit(text)

    def _on_return(self) -> None:
        text = self.text().strip()
        if not text:
            return
        match = self._search.best_match(text)
        if match:
            self.setText(match)
            self.itemChosen.emit(match)
        else:
            self.itemChosen.emit(text)

    # --- API pública -------------------------------------------------------

    def set_value(self, value: str) -> None:
        self.blockSignals(True)
        self.setText(value)
        self.blockSignals(False)
