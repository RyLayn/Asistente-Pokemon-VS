"""Pantalla de selección de combate (Bring 6 Pick 3/4).

Muestra los seis Pokémon del rival como referencia y permite elegir los
Pokémon propios que entrarán a la batalla (3 en individual, 4 en dobles).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import MODE_SINGLES, PICK_COUNT
from app.core import battle_analyzer
from app.models.pokemon_set import PokemonSet
from app.models.team import Team
from app.services.database_service import DatabaseService
from app.services.sprite_service import SpriteService
from app.ui.widgets.sprite_label import SpriteLabel


class PickChip(QFrame):
    """Tarjeta con sprite + nombre; opcionalmente seleccionable."""

    clicked = Signal()

    def __init__(
        self, db: DatabaseService, sprites: SpriteService,
        selectable: bool = True, parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._selectable = selectable
        self._selected = False
        self.setObjectName("PickChip")
        self.setProperty("selected", False)
        if selectable:
            self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        self.sprite = SpriteLabel(db, sprites, size=72)
        self.name = QLabel("—")
        self.name.setAlignment(Qt.AlignCenter)
        self.name.setWordWrap(True)
        layout.addWidget(self.sprite, 0, Qt.AlignCenter)
        layout.addWidget(self.name)

    def set_species(self, species: str, display: str) -> None:
        self.sprite.set_species(species)
        self.name.setText(display or "—")
        self.setEnabled(bool(species))

    def set_selected(self, value: bool) -> None:
        self._selected = value
        self.setProperty("selected", value)
        # Forzar re-aplicación del estilo.
        self.style().unpolish(self)
        self.style().polish(self)

    def is_selected(self) -> bool:
        return self._selected

    def mousePressEvent(self, event) -> None:  # noqa: N802 (API Qt)
        if self._selectable and self.isEnabled():
            self.clicked.emit()
        super().mousePressEvent(event)


class PickPanel(QWidget):
    """Selección de los Pokémon propios para la batalla."""

    picksChanged = Signal()

    def __init__(
        self,
        db: DatabaseService,
        sprites: SpriteService,
        mode: str = MODE_SINGLES,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._sprites = sprites
        self._mode = mode
        self._user_team = Team(name="Mi equipo")
        self._enemy_team = Team(name="Equipo rival", is_enemy=True)
        self._selected: list[int] = []
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)

        header = QLabel("Selección de combate")
        header.setObjectName("Title")
        outer.addWidget(header)

        # Rival (referencia).
        rival_title = QLabel("Equipo rival")
        rival_title.setObjectName("SectionTitle")
        outer.addWidget(rival_title)
        self.rival_grid = QGridLayout()
        self.rival_grid.setSpacing(8)
        self.rival_chips: list[PickChip] = []
        rival_wrap = QFrame()
        rival_wrap.setObjectName("Card")
        rwl = QHBoxLayout(rival_wrap)
        rwl.setContentsMargins(10, 10, 10, 10)
        for i in range(6):
            chip = PickChip(self._db, self._sprites, selectable=False)
            self.rival_chips.append(chip)
            rwl.addWidget(chip)
        outer.addWidget(rival_wrap)

        # Selección propia.
        self.pick_title = QLabel("Elige tu equipo de batalla")
        self.pick_title.setObjectName("SectionTitle")
        outer.addWidget(self.pick_title)
        self.own_chips: list[PickChip] = []
        own_wrap = QFrame()
        own_wrap.setObjectName("Card")
        owl = QHBoxLayout(own_wrap)
        owl.setContentsMargins(10, 10, 10, 10)
        for i in range(6):
            chip = PickChip(self._db, self._sprites, selectable=True)
            chip.clicked.connect(lambda idx=i: self._toggle(idx))
            self.own_chips.append(chip)
            owl.addWidget(chip)
        outer.addWidget(own_wrap)

        self.counter = QLabel()
        self.counter.setObjectName("Subtitle")
        outer.addWidget(self.counter)

        # Sugerencia (posible elección) frente al equipo rival.
        sug = QFrame()
        sug.setObjectName("Card")
        sl = QVBoxLayout(sug)
        sl.setContentsMargins(14, 12, 14, 12)
        sl.setSpacing(6)
        sug_title = QLabel("Sugerencia frente a este rival")
        sug_title.setObjectName("SectionTitle")
        sl.addWidget(sug_title)
        exp = QLabel("No sabemos qué Pokémon sacará el rival, pero según su equipo "
                     "completo estos son los que mejor encajan (posible elección):")
        exp.setObjectName("Subtitle")
        exp.setWordWrap(True)
        sl.addWidget(exp)
        self.suggestion = QLabel("—")
        self.suggestion.setObjectName("CardBody")
        self.suggestion.setWordWrap(True)
        sl.addWidget(self.suggestion)
        self.apply_btn = QPushButton("Usar esta sugerencia")
        self.apply_btn.setCursor(Qt.PointingHandCursor)
        self.apply_btn.clicked.connect(self._apply_suggestion)
        sl.addWidget(self.apply_btn, 0, Qt.AlignLeft)
        outer.addWidget(sug)

        outer.addStretch(1)
        self._suggested_idx: list[int] = []
        self._update_counter()

    # --- API ---------------------------------------------------------------

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        target = PICK_COUNT[mode]
        if len(self._selected) > target:
            self._selected = self._selected[:target]
        elif len(self._selected) < target:
            # Completar con los siguientes activos disponibles.
            for i, m in enumerate(self._user_team.members):
                if len(self._selected) >= target:
                    break
                if not m.is_empty and i not in self._selected:
                    self._selected.append(i)
        self._refresh()
        self.picksChanged.emit()

    def set_teams(self, user_team: Team, enemy_team: Team) -> None:
        self._user_team = user_team
        self._enemy_team = enemy_team
        # Selección por defecto: los primeros N activos.
        active_idx = [i for i, m in enumerate(user_team.members) if not m.is_empty]
        self._selected = active_idx[: PICK_COUNT[self._mode]]
        self._refresh()
        self.picksChanged.emit()

    def picks(self) -> list[PokemonSet]:
        return [self._user_team.members[i] for i in self._selected]

    def sync(self) -> None:
        """Refresca sprites/nombres y descarta selecciones que quedaron vacías,
        sin reiniciar la elección del usuario."""
        self._selected = [i for i in self._selected
                          if not self._user_team.members[i].is_empty]
        self._refresh()
        self.picksChanged.emit()

    # --- Interno -----------------------------------------------------------

    def _toggle(self, index: int) -> None:
        if self._user_team.members[index].is_empty:
            return
        if index in self._selected:
            self._selected.remove(index)
        else:
            if len(self._selected) >= PICK_COUNT[self._mode]:
                return  # límite alcanzado
            self._selected.append(index)
        self._refresh_selection()
        self._update_counter()
        self.picksChanged.emit()

    def _refresh(self) -> None:
        for chip, member in zip(self.rival_chips, self._enemy_team.members):
            mon = self._db.get_pokemon(member.species)
            chip.set_species(member.species, mon.display_name if mon else member.species)
        for chip, member in zip(self.own_chips, self._user_team.members):
            mon = self._db.get_pokemon(member.species)
            chip.set_species(member.species, mon.display_name if mon else member.species)
        self._refresh_selection()
        self._update_counter()
        self._update_suggestion()

    def _update_suggestion(self) -> None:
        if not hasattr(self, "suggestion"):
            return
        enemies = [m for m in self._enemy_team.members if not m.is_empty]
        own = [m for m in self._user_team.members if not m.is_empty]
        target = PICK_COUNT[self._mode]
        if not enemies or len(own) < 1:
            self.suggestion.setText("Define tu equipo y el del rival para ver la sugerencia.")
            self._suggested_idx = []
            self.apply_btn.setEnabled(False)
            return
        table = battle_analyzer.build_priority_table(own, enemies, self._db)
        best = table.matchups[:target]
        self._suggested_idx = []
        for m in best:
            for i, member in enumerate(self._user_team.members):
                mon = self._db.get_pokemon(member.species)
                disp = mon.display_name if mon else member.species
                if disp == m.species and i not in self._suggested_idx:
                    self._suggested_idx.append(i)
                    break
        if best:
            self.suggestion.setText("   ·   ".join(f"{m.species} {m.stars_text}" for m in best))
            self.apply_btn.setEnabled(bool(self._suggested_idx))
        else:
            self.suggestion.setText("—")
            self.apply_btn.setEnabled(False)

    def _apply_suggestion(self) -> None:
        if not self._suggested_idx:
            return
        self._selected = self._suggested_idx[: PICK_COUNT[self._mode]]
        self._refresh_selection()
        self._update_counter()
        self.picksChanged.emit()

    def _refresh_selection(self) -> None:
        for i, chip in enumerate(self.own_chips):
            chip.set_selected(i in self._selected)

    def _update_counter(self) -> None:
        total = PICK_COUNT[self._mode]
        self.counter.setText(
            f"Seleccionados: {len(self._selected)} / {total}  ·  "
            f"toca un Pokémon para añadirlo o quitarlo."
        )
        self.pick_title.setText(f"Elige {total} Pokémon para la batalla")
