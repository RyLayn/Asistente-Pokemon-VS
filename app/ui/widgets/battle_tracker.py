"""Marcador de combate en vivo.

Permite marcar qué Pokémon han sido debilitados en cada bando, indicar quién
los derrotó, ver cuántos quedan en pie y un registro de los derribos. La
información alimenta el análisis de la pantalla de combate (los Pokémon
debilitados se excluyen).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.models.team import Team
from app.services.battle_state import BattleState
from app.services.database_service import DatabaseService
from app.services.sprite_service import SpriteService
from app.ui.widgets.sprite_label import SpriteLabel


class _MemberRow(QFrame):
    """Fila de un Pokémon: sprite, nombre, casilla de debilitado y quién lo derrotó."""

    def __init__(self, db, sprites, state: BattleState, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self._db = db
        self._state = state
        self._member = None
        self._name = ""

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(10)

        self.sprite = SpriteLabel(db, sprites, size=44)
        lay.addWidget(self.sprite)

        self.label = QLabel("—")
        self.label.setMinimumWidth(150)
        lay.addWidget(self.label, 1)

        self.ko = QCheckBox("Debilitado")
        self.ko.setObjectName("KOToggle")
        self.ko.toggled.connect(self._on_toggle)
        lay.addWidget(self.ko)

        self.by = QComboBox()
        self.by.setMinimumWidth(150)
        self.by.setToolTip("¿Quién lo debilitó?")
        lay.addWidget(self.by)

    def set_member(self, member, name: str, opponents: list[str]) -> None:
        self._member = member
        self._name = name
        self.sprite.set_species(member.species if member else "")
        self.label.setText(name if member else "—")
        self.by.blockSignals(True)
        self.by.clear()
        self.by.addItem("¿quién lo debilitó?", "")
        for o in opponents:
            self.by.addItem(o, o)
        self.by.blockSignals(False)
        self.ko.blockSignals(True)
        self.ko.setChecked(bool(member) and self._state.is_fainted(member))
        self.ko.blockSignals(False)
        visible = bool(member)
        self.setVisible(visible)

    def _on_toggle(self, checked: bool) -> None:
        if self._member is None:
            return
        self._state.set_fainted(self._member, checked, self._name,
                                self.by.currentData() or "")


class BattleTracker(QWidget):
    """Pantalla de marcador: estado de ambos equipos durante el combate."""

    def __init__(
        self,
        db: DatabaseService,
        sprites: SpriteService,
        state: BattleState,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._sprites = sprites
        self._state = state
        self._user_team = Team(name="Tu equipo")
        self._enemy_team = Team(name="Equipo rival", is_enemy=True)
        self._user_rows: list[_MemberRow] = []
        self._enemy_rows: list[_MemberRow] = []
        self._build()
        self._state.changed.connect(self._refresh_counts_and_log)

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)

        header = QLabel("Marcador del combate")
        header.setObjectName("Title")
        outer.addWidget(header)

        self.counter = QLabel("—")
        self.counter.setObjectName("Subtitle")
        outer.addWidget(self.counter)

        cols = QHBoxLayout()
        cols.setSpacing(14)
        cols.addLayout(self._team_column("Tu equipo", self._user_rows), 1)
        cols.addLayout(self._team_column("Equipo rival", self._enemy_rows), 1)
        outer.addLayout(cols)

        # Registro de derribos.
        log_card = QFrame()
        log_card.setObjectName("Card")
        lc = QVBoxLayout(log_card)
        lc.setContentsMargins(14, 12, 14, 12)
        t = QLabel("Registro")
        t.setObjectName("SectionTitle")
        lc.addWidget(t)
        self.log_label = QLabel("Marca a un Pokémon como debilitado para empezar el registro.")
        self.log_label.setObjectName("CardBody")
        self.log_label.setWordWrap(True)
        lc.addWidget(self.log_label)
        outer.addWidget(log_card)

        reset = QPushButton("Reiniciar marcador")
        reset.setCursor(Qt.PointingHandCursor)
        reset.clicked.connect(self._state.reset)
        outer.addWidget(reset, 0, Qt.AlignLeft)
        outer.addStretch(1)

    def _team_column(self, title: str, rows: list[_MemberRow]) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(6)
        t = QLabel(title)
        t.setObjectName("SectionTitle")
        col.addWidget(t)
        for _ in range(6):
            row = _MemberRow(self._db, self._sprites, self._state)
            rows.append(row)
            col.addWidget(row)
        col.addStretch(1)
        return col

    # --- API ---------------------------------------------------------------

    def set_teams(self, user_team: Team, enemy_team: Team) -> None:
        self._user_team = user_team
        self._enemy_team = enemy_team
        self._reload()

    def _names(self, team: Team) -> list[str]:
        out = []
        for m in team.members:
            if not m.is_empty:
                mon = self._db.get_pokemon(m.species)
                out.append(mon.display_name if mon else m.species)
        return out

    def _reload(self) -> None:
        enemy_names = self._names(self._enemy_team)
        user_names = self._names(self._user_team)
        for row, member in zip(self._user_rows, self._user_team.members):
            mon = self._db.get_pokemon(member.species) if not member.is_empty else None
            name = mon.display_name if mon else member.species
            row.set_member(None if member.is_empty else member, name, enemy_names)
        for row, member in zip(self._enemy_rows, self._enemy_team.members):
            mon = self._db.get_pokemon(member.species) if not member.is_empty else None
            name = mon.display_name if mon else member.species
            row.set_member(None if member.is_empty else member, name, user_names)
        self._refresh_counts_and_log()

    def _refresh_counts_and_log(self) -> None:
        ua = self._state.count_alive(self._user_team.members)
        ut = sum(1 for m in self._user_team.members if not m.is_empty)
        ea = self._state.count_alive(self._enemy_team.members)
        et = sum(1 for m in self._enemy_team.members if not m.is_empty)
        self.counter.setText(
            f"En pie — Tú: {ua}/{ut}   ·   Rival: {ea}/{et}"
        )
        if self._state.log:
            self.log_label.setText("\n".join(f"• {line}" for line in self._state.log[-12:]))
        else:
            self.log_label.setText("Marca a un Pokémon como debilitado para empezar el registro.")
