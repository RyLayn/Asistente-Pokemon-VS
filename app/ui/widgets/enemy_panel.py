"""Panel del equipo rival: solo especies, con sprite como referencia visual."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.models.team import Team
from app.services.database_service import DatabaseService
from app.services.search_service import SearchService
from app.services.sprite_service import SpriteService
from app.ui.widgets.search_box import SearchBox
from app.ui.widgets.sprite_label import SpriteLabel, make_icon_provider


class EnemyPanel(QWidget):
    """Seis selectores de especie para el equipo rival."""

    teamChanged = Signal()

    def __init__(
        self,
        db: DatabaseService,
        sprites: SpriteService,
        pokemon_search: SearchService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._sprites = sprites
        self._team = Team(name="Equipo rival", is_enemy=True)
        self._boxes: list[SearchBox] = []
        self._icons: list[SpriteLabel] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        header = QLabel("Equipo rival")
        header.setObjectName("Title")
        outer.addWidget(header)
        subtitle = QLabel("Indica las seis especies del rival.")
        subtitle.setObjectName("Subtitle")
        outer.addWidget(subtitle)

        for i in range(6):
            card = QFrame()
            card.setObjectName("Card")
            row = QHBoxLayout(card)
            row.setContentsMargins(10, 8, 10, 8)
            row.setSpacing(10)
            icon = SpriteLabel(self._db, self._sprites, size=56)
            box = SearchBox(pokemon_search, f"Rival {i + 1}…",
                icon_provider=make_icon_provider(self._db, self._sprites))
            box.itemChosen.connect(lambda name, idx=i: self._on_chosen(idx, name))
            box.editingFinished.connect(lambda idx=i: self._on_edited(idx))
            row.addWidget(icon, 0, Qt.AlignVCenter)
            row.addWidget(box, 1)
            self._icons.append(icon)
            self._boxes.append(box)
            outer.addWidget(card)

        outer.addStretch(1)
        self._rebind()

    def set_team(self, team: Team) -> None:
        self._team = team
        self._team.is_enemy = True
        self._rebind()

    def team(self) -> Team:
        return self._team

    def _rebind(self) -> None:
        for box, icon, member in zip(self._boxes, self._icons, self._team.members):
            box.set_value(member.species)
            icon.set_species(member.species)

    def _on_chosen(self, index: int, name: str) -> None:
        resolved = self._db.resolve_species(name)
        self._team.members[index].species = resolved
        self._boxes[index].set_value(resolved)
        self._icons[index].set_species(resolved)
        self.teamChanged.emit()

    def _on_edited(self, index: int) -> None:
        text = self._boxes[index].text().strip()
        resolved = self._db.resolve_species(text) if text else ""
        self._team.members[index].species = resolved
        self._icons[index].set_species(resolved)
        self.teamChanged.emit()
