"""Constructor del equipo del usuario.

Diseño guiado: a la izquierda, seis ranuras compactas (sprite + nombre + tipos);
al pulsar una, a la derecha aparece el editor detallado SOLO de ese Pokémon,
organizado en secciones para no abrumar.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core import natures, type_chart
from app.models.pokemon_set import PokemonSet
from app.models.team import Team
from app.services.database_service import DatabaseService
from app.services.search_service import SearchService
from app.services.sprite_service import SpriteService
from app.ui.widgets.search_box import SearchBox
from app.ui.widgets.sprite_label import SpriteLabel, make_icon_provider
from app.ui.widgets import type_badge


class TeamSlot(QFrame):
    """Ranura compacta seleccionable del equipo (sprite + nombre + tipos)."""

    clicked = Signal()

    def __init__(self, index: int, db: DatabaseService, sprites: SpriteService, parent=None):
        super().__init__(parent)
        self._db = db
        self._index = index
        self.setObjectName("PickChip")
        self.setProperty("selected", False)
        self.setCursor(Qt.PointingHandCursor)
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 8, 10, 8)
        row.setSpacing(10)
        self.sprite = SpriteLabel(db, sprites, size=52)
        text = QVBoxLayout()
        text.setSpacing(1)
        self.name = QLabel(f"Ranura {index + 1}")
        self.name.setObjectName("SlotName")
        self.types = QLabel("vacío")
        self.types.setObjectName("Subtitle")
        text.addWidget(self.name)
        text.addWidget(self.types)
        row.addWidget(self.sprite)
        row.addLayout(text, 1)

    def set_species(self, species: str) -> None:
        self.sprite.set_species(species)
        mon = self._db.get_pokemon(species) if species else None
        if mon:
            self.name.setText(self._db.localized_pokemon(mon))
            self.types.setTextFormat(Qt.RichText)
            self.types.setText(type_badge.pills_html(mon.types))
        else:
            self.name.setText(f"Ranura {self._index + 1}")
            self.types.setTextFormat(Qt.PlainText)
            self.types.setText("vacío · toca para añadir")

    def set_selected(self, value: bool) -> None:
        self.setProperty("selected", value)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):  # noqa: N802
        self.clicked.emit()
        super().mousePressEvent(event)


def _section(title: str) -> QLabel:
    lbl = QLabel(title)
    lbl.setObjectName("SectionTitle")
    return lbl


class LevelSelector(QWidget):
    """Selector de nivel con botones grandes − y +."""

    valueChanged = Signal(int)

    def __init__(self, value: int = 50, parent=None):
        super().__init__(parent)
        self._value = value
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self.minus = QPushButton("−")
        self.minus.setObjectName("StepBtn")
        self.minus.setFixedSize(40, 40)
        self.minus.setCursor(Qt.PointingHandCursor)
        self.minus.clicked.connect(lambda: self._step(-1))
        self.display = QLabel(str(value))
        self.display.setObjectName("LevelDisplay")
        self.display.setAlignment(Qt.AlignCenter)
        self.display.setFixedWidth(64)
        self.plus = QPushButton("+")
        self.plus.setObjectName("StepBtn")
        self.plus.setFixedSize(40, 40)
        self.plus.setCursor(Qt.PointingHandCursor)
        self.plus.clicked.connect(lambda: self._step(1))
        row.addWidget(self.minus)
        row.addWidget(self.display)
        row.addWidget(self.plus)

    def _step(self, delta: int) -> None:
        self.setValue(self._value + delta)
        self.valueChanged.emit(self._value)

    def value(self) -> int:
        return self._value

    def setValue(self, v: int) -> None:
        self._value = max(1, min(100, v))
        self.display.setText(str(self._value))


class PokemonSetEditor(QWidget):
    """Editor detallado de una ranura, en secciones."""

    changed = Signal()

    def __init__(self, db, sprites, pokemon_search, move_search, item_search, ability_search, parent=None):
        super().__init__(parent)
        self._db = db
        self._sprites = sprites
        self._pokemon_search = pokemon_search
        self._move_search = move_search
        self._item_search = item_search
        self._ability_search = ability_search
        self._pset = PokemonSet()
        self._loading = False
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(12)

        # Cabecera: sprite grande + especie + nivel.
        head = QHBoxLayout()
        head.setSpacing(14)
        self.sprite = SpriteLabel(self._db, self._sprites, size=120)
        head.addWidget(self.sprite, 0, Qt.AlignTop)

        head_fields = QVBoxLayout()
        head_fields.setSpacing(6)
        head_fields.addWidget(_section("Pokémon"))
        self.species_box = SearchBox(self._pokemon_search, "Escribe un Pokémon…",
            icon_provider=make_icon_provider(self._db, self._sprites))
        self.species_box.itemChosen.connect(self._on_species_chosen)
        head_fields.addWidget(self.species_box)

        lvl_row = QHBoxLayout()
        lvl_row.setSpacing(8)
        lvl_label = QLabel("Nivel")
        lvl_label.setObjectName("FieldLabel")
        self.level_spin = LevelSelector(50)
        self.level_spin.valueChanged.connect(self._on_field_changed)
        lvl_row.addWidget(lvl_label)
        lvl_row.addWidget(self.level_spin)
        lvl_row.addStretch(1)
        head_fields.addLayout(lvl_row)
        head.addLayout(head_fields, 1)
        root.addLayout(head)

        # Naturaleza + Tera.
        root.addWidget(_section("Naturaleza y Teratipo"))
        nt = QHBoxLayout()
        nt.setSpacing(8)
        self.nature_combo = QComboBox()
        self.nature_combo.addItems(natures.all_nature_names())
        self.nature_combo.setCurrentText("Seria")
        self.nature_combo.currentTextChanged.connect(self._on_field_changed)
        self.tera_combo = QComboBox()
        self.tera_combo.addItem("Sin Teratipo", "")
        for t in type_chart.TYPES:
            self.tera_combo.addItem(f"Tera {t}", t)
        self.tera_combo.currentIndexChanged.connect(self._on_field_changed)
        nt.addWidget(self.nature_combo, 1)
        nt.addWidget(self.tera_combo, 1)
        root.addLayout(nt)

        # Habilidad + objeto.
        root.addWidget(_section("Habilidad y objeto"))
        ho = QHBoxLayout()
        ho.setSpacing(8)
        self.ability_combo = QComboBox()
        self.ability_combo.setEditable(False)
        self.ability_combo.currentIndexChanged.connect(self._on_field_changed)
        self.item_box = SearchBox(self._item_search, "Objeto (toca y escribe)…")
        self.item_box.itemChosen.connect(self._on_field_changed)
        self.item_box.editingFinished.connect(self._on_field_changed)
        ho.addWidget(self.ability_combo, 1)
        ho.addWidget(self.item_box, 1)
        root.addLayout(ho)

        # Movimientos.
        root.addWidget(_section("Movimientos"))
        moves = QGridLayout()
        moves.setHorizontalSpacing(8)
        moves.setVerticalSpacing(8)
        self.move_boxes: list[SearchBox] = []
        for i in range(4):
            box = SearchBox(self._move_search, f"Movimiento {i + 1}…")
            box.itemChosen.connect(self._on_field_changed)
            box.editingFinished.connect(self._on_field_changed)
            moves.addWidget(box, i // 2, i % 2)
            self.move_boxes.append(box)
        root.addLayout(moves)
        root.addStretch(1)

    # --- Vinculación -------------------------------------------------------

    def bind(self, pset: PokemonSet) -> None:
        self._loading = True
        self._pset = pset
        self.species_box.set_value(pset.species)
        self.sprite.set_species(pset.species)
        self.level_spin.setValue(pset.level)
        self.nature_combo.setCurrentText(pset.nature or "Seria")
        self._refresh_abilities(pset.species, pset.ability)
        self.item_box.set_value(pset.item)
        idx = self.tera_combo.findData(pset.tera_type) if pset.tera_type else 0
        self.tera_combo.setCurrentIndex(max(idx, 0))
        for box, move in zip(self.move_boxes, pset.moves):
            box.set_value(move)
        self._loading = False

    def _refresh_abilities(self, species: str, current: str = "") -> None:
        self.ability_combo.blockSignals(True)
        self.ability_combo.clear()
        self.ability_combo.addItem("Sin habilidad", "")
        mon = self._db.get_pokemon(species) if species else None
        if mon and mon.abilities:
            for ab in mon.abilities:
                self.ability_combo.addItem(self._db.localized_ability(ab), ab)
        if current:
            i = self.ability_combo.findData(current)
            if i < 0:
                self.ability_combo.addItem(self._db.localized_ability(current), current)
                i = self.ability_combo.count() - 1
            self.ability_combo.setCurrentIndex(i)
        else:
            self.ability_combo.setCurrentIndex(0)
        self.ability_combo.blockSignals(False)

    # --- Eventos -----------------------------------------------------------

    def _on_species_chosen(self, name: str) -> None:
        if self._loading:
            return
        resolved = self._db.resolve_species(name)
        self._pset.species = resolved
        self.sprite.set_species(resolved)
        self._refresh_abilities(resolved)
        mon = self._db.get_pokemon(resolved)
        if mon and mon.types and not self._pset.tera_type:
            i = self.tera_combo.findData(mon.types[0])
            if i >= 0:
                self.tera_combo.setCurrentIndex(i)
        self._commit()

    def _on_field_changed(self, *_a) -> None:
        if self._loading:
            return
        self._commit()

    def _commit(self) -> None:
        text = self.species_box.text().strip()
        self._pset.species = self._db.resolve_species(text) if text else ""
        self.sprite.set_species(self._pset.species)
        self._pset.level = self.level_spin.value()
        self._pset.nature = self.nature_combo.currentText()
        self._pset.ability = self.ability_combo.currentData() or ""
        self._pset.item = self.item_box.text().strip()
        self._pset.tera_type = self.tera_combo.currentData() or ""
        self._pset.moves = [b.text().strip() for b in self.move_boxes]
        self.changed.emit()




class TeamBuilder(QWidget):
    """Seis ranuras + editor del Pokémon seleccionado."""

    teamChanged = Signal()

    def __init__(self, db, sprites, pokemon_search, move_search, item_search, ability_search, parent=None):
        super().__init__(parent)
        self._db = db
        self._sprites = sprites
        self._team = Team(name="Mi equipo")
        self._active = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)
        header = QLabel("Tu equipo")
        header.setObjectName("Title")
        outer.addWidget(header)
        hint = QLabel("Toca una ranura para editar ese Pokémon.")
        hint.setObjectName("Subtitle")
        outer.addWidget(hint)

        body = QHBoxLayout()
        body.setSpacing(14)
        outer.addLayout(body, 1)

        # Columna de ranuras.
        slots_col = QVBoxLayout()
        slots_col.setSpacing(8)
        self._slots: list[TeamSlot] = []
        for i in range(6):
            slot = TeamSlot(i, db, sprites)
            slot.clicked.connect(lambda idx=i: self.select(idx))
            self._slots.append(slot)
            slots_col.addWidget(slot)
        slots_col.addStretch(1)
        slots_wrap = QWidget()
        slots_wrap.setLayout(slots_col)
        slots_wrap.setFixedWidth(240)
        body.addWidget(slots_wrap)

        # Panel del editor.
        self._editor = PokemonSetEditor(
            db, sprites, pokemon_search, move_search, item_search, ability_search
        )
        editor_card = QFrame()
        editor_card.setObjectName("Card")
        el = QVBoxLayout(editor_card)
        el.setContentsMargins(16, 16, 16, 16)
        el.addWidget(self._editor)
        body.addWidget(editor_card, 1)

        self._editor.changed.connect(self._on_editor_changed)
        self._rebind()
        self.select(0)

    def set_team(self, team: Team) -> None:
        self._team = team
        self._rebind()
        self.select(self._active)

    def team(self) -> Team:
        return self._team

    def select(self, index: int) -> None:
        self._active = index
        for i, slot in enumerate(self._slots):
            slot.set_selected(i == index)
        self._editor.bind(self._team.members[index])

    def _on_editor_changed(self) -> None:
        member = self._team.members[self._active]
        self._slots[self._active].set_species(member.species)
        self.teamChanged.emit()

    def _rebind(self) -> None:
        for slot, member in zip(self._slots, self._team.members):
            slot.set_species(member.species)
