"""Pantalla de combate adaptada al modo (Individual / Dobles).

Muestra el enfrentamiento con sprites grandes y tarjetas de recomendación
claras. Permite **megaevolucionar** en pleno combate (propias y rival) para
recalcular con las características de la forma mega, avisa del mejor momento
para hacerlo (y recuerda la regla de una megaevolución por combate), y compara
la velocidad de los activos.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.config import ACTIVE_COUNT, MODE_DOUBLES, MODE_SINGLES
from app.core import battle_analyzer, type_chart
from app.models.pokemon_set import PokemonSet
from app.models.team import Team
from app.services.database_service import DatabaseService
from app.services.sprite_service import SpriteService
from app.ui.widgets.sprite_label import SpriteLabel


def _info_card(title: str) -> tuple[QFrame, QLabel]:
    card = QFrame()
    card.setObjectName("Card")
    lay = QVBoxLayout(card)
    lay.setContentsMargins(14, 12, 14, 12)
    lay.setSpacing(4)
    t = QLabel(title)
    t.setObjectName("SectionTitle")
    body = QLabel("—")
    body.setWordWrap(True)
    body.setObjectName("CardBody")
    lay.addWidget(t)
    lay.addWidget(body)
    return card, body


class BattleScreen(QWidget):
    """Análisis de enfrentamiento con sprites, megaevolución y recomendaciones."""

    def __init__(
        self,
        db: DatabaseService,
        sprites: SpriteService,
        mode: str = MODE_SINGLES,
        state=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._sprites = sprites
        self._mode = mode
        self._state = state
        self._picks: list[PokemonSet] = []
        self._enemy_team = Team(name="Equipo rival", is_enemy=True)
        self._own_combos: list[QComboBox] = []
        self._own_sprites: list[SpriteLabel] = []
        self._own_mega: list[QCheckBox] = []
        self._rival_combos: list[QComboBox] = []
        self._rival_sprites: list[SpriteLabel] = []
        self._rival_mega: list[QCheckBox] = []
        self._build()

    # --- Construcción ------------------------------------------------------

    def _build(self) -> None:
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(12)

        self.header = QLabel("Combate")
        self.header.setObjectName("Title")
        self._outer.addWidget(self.header)

        self.counts = QLabel("")
        self.counts.setObjectName("Subtitle")
        self._outer.addWidget(self.counts)

        self.board = QFrame()
        self.board.setObjectName("Card")
        self._outer.addWidget(self.board)

        self.rec_grid = QGridLayout()
        self.rec_grid.setSpacing(10)
        self.move_card, self.move_body = _info_card("Mejor ataque")
        self.switch_card, self.switch_body = _info_card("Mejor cambio")
        self.adv_card, self.adv_body = _info_card("Ventajas, desventajas y velocidad")
        self.cover_card, self.cover_body = _info_card("Cobertura")
        self.mega_card, self.mega_body = _info_card("Megaevolución")
        self.rec_grid.addWidget(self.move_card, 0, 0)
        self.rec_grid.addWidget(self.switch_card, 0, 1)
        self.rec_grid.addWidget(self.adv_card, 1, 0)
        self.rec_grid.addWidget(self.cover_card, 1, 1)
        self.rec_grid.addWidget(self.mega_card, 2, 0, 1, 2)
        self._outer.addLayout(self.rec_grid)
        self._outer.addStretch(1)

        self._build_board()

    def _build_board(self) -> None:
        old = self.board.layout()
        if old is not None:
            QWidget().setLayout(old)
        self._own_combos.clear()
        self._own_sprites.clear()
        self._own_mega.clear()
        self._rival_combos.clear()
        self._rival_sprites.clear()
        self._rival_mega.clear()

        layout = QHBoxLayout(self.board)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        n = ACTIVE_COUNT[self._mode]
        layout.addLayout(self._side_column("Tu campo", n, own=True), 1)

        vs = QLabel("VS")
        vs.setObjectName("VsLabel")
        vs.setAlignment(Qt.AlignCenter)
        layout.addWidget(vs)

        layout.addLayout(self._side_column("Campo rival", n, own=False), 1)

    def _side_column(self, title: str, n: int, own: bool) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(8)
        t = QLabel(title)
        t.setObjectName("SectionTitle")
        t.setAlignment(Qt.AlignCenter)
        col.addWidget(t)

        slots = QHBoxLayout()
        slots.setSpacing(10)
        for _ in range(n):
            slot = QVBoxLayout()
            slot.setSpacing(4)
            sprite = SpriteLabel(self._db, self._sprites, size=110)
            combo = QComboBox()
            mega = QCheckBox("Megaevolucionar")
            mega.setObjectName("MegaToggle")
            mega.setVisible(False)
            mega.toggled.connect(self._on_slot_change)
            combo.currentIndexChanged.connect(self._on_slot_change)
            slot.addWidget(sprite, 0, Qt.AlignCenter)
            slot.addWidget(combo)
            slot.addWidget(mega, 0, Qt.AlignCenter)
            slots.addLayout(slot)
            if own:
                self._own_sprites.append(sprite)
                self._own_combos.append(combo)
                self._own_mega.append(mega)
            else:
                self._rival_sprites.append(sprite)
                self._rival_combos.append(combo)
                self._rival_mega.append(mega)
        col.addLayout(slots)
        return col

    # --- Datos -------------------------------------------------------------

    def set_mode(self, mode: str) -> None:
        if mode == self._mode:
            return
        self._mode = mode
        self._build_board()
        self._reload_combos()
        self._refresh_analysis()

    def set_battle(self, picks: list[PokemonSet], enemy_team: Team) -> None:
        self._picks = [p for p in picks if not p.is_empty]
        self._enemy_team = enemy_team
        self._reload_combos()
        self._refresh_analysis()

    def refresh(self) -> None:
        self._reload_combos()
        self._refresh_analysis()

    def _alive(self, members: list[PokemonSet]) -> list[PokemonSet]:
        if self._state is not None:
            return self._state.alive(members)
        return [m for m in members if not m.is_empty]

    def _reload_combos(self) -> None:
        picks = self._alive(self._picks)
        for k, combo in enumerate(self._own_combos):
            combo.blockSignals(True)
            combo.clear()
            for member in picks:
                mon = self._db.get_pokemon(member.species)
                combo.addItem(mon.display_name if mon else member.species, member)
            if combo.count() > k:
                combo.setCurrentIndex(k)
            combo.blockSignals(False)
        rivals = self._alive(self._enemy_team.active_members)
        for k, combo in enumerate(self._rival_combos):
            combo.blockSignals(True)
            combo.clear()
            for member in rivals:
                mon = self._db.get_pokemon(member.species)
                combo.addItem(mon.display_name if mon else member.species, member)
            if combo.count() > k:
                combo.setCurrentIndex(k)
            combo.blockSignals(False)
        self._configure_mega_toggles()
        self._update_sprites()
        self._update_counts()

    def _update_counts(self) -> None:
        ua = len(self._alive(self._picks))
        ut = len([m for m in self._picks if not m.is_empty])
        ea = len(self._alive(self._enemy_team.active_members))
        et = len([m for m in self._enemy_team.active_members if not m.is_empty])
        self.counts.setText(f"En pie — Tú: {ua}/{ut}   ·   Rival: {ea}/{et}"
                            "   (marca debilitados en la pestaña Marcador)")

    def _mega_form_for(self, member: Optional[PokemonSet]) -> str:
        """Forma mega aplicable a un set (según su piedra o, si no, la primera)."""
        if not member:
            return ""
        by_item = self._db.mega_for_item(member.species, member.item)
        if by_item:
            return by_item
        opts = self._db.mega_options(member.species)
        return opts[0]["form"] if opts else ""

    def _configure_mega_toggles(self) -> None:
        for combo, mega in list(zip(self._own_combos, self._own_mega)) + \
                            list(zip(self._rival_combos, self._rival_mega)):
            member = combo.currentData()
            form = self._mega_form_for(member)
            mega.blockSignals(True)
            if form:
                mega.setText(f"Megaevolucionar → {form}")
                mega.setVisible(True)
            else:
                mega.setChecked(False)
                mega.setVisible(False)
            mega.blockSignals(False)

    def _on_slot_change(self, *_) -> None:
        self._configure_mega_toggles()
        self._refresh_analysis()

    def _update_sprites(self) -> None:
        for combo, sprite, mega in zip(self._own_combos, self._own_sprites, self._own_mega):
            sprite.set_species(self._effective_species(combo, mega))
        for combo, sprite, mega in zip(self._rival_combos, self._rival_sprites, self._rival_mega):
            sprite.set_species(self._effective_species(combo, mega))

    # --- Megaevolución -----------------------------------------------------

    def _effective_species(self, combo: QComboBox, mega: QCheckBox) -> str:
        member = combo.currentData()
        if not member:
            return ""
        if mega.isChecked():
            form = self._mega_form_for(member)
            if form:
                return form
        return member.species

    def _effective_set(self, combo: QComboBox, mega: QCheckBox) -> Optional[PokemonSet]:
        member = combo.currentData()
        if not member:
            return None
        sp = self._effective_species(combo, mega)
        if sp != member.species:
            return replace(member, species=sp)
        return member

    # --- Análisis ----------------------------------------------------------

    def _own_active(self) -> list[PokemonSet]:
        seen, out = set(), []
        for combo, mega in zip(self._own_combos, self._own_mega):
            s = self._effective_set(combo, mega)
            if s and id(combo.currentData()) not in seen:
                seen.add(id(combo.currentData()))
                out.append(s)
        return out

    def _rival_active(self) -> list[PokemonSet]:
        seen, out = set(), []
        for combo, mega in zip(self._rival_combos, self._rival_mega):
            s = self._effective_set(combo, mega)
            if s and id(combo.currentData()) not in seen:
                seen.add(id(combo.currentData()))
                out.append(s)
        return out

    def _refresh_analysis(self) -> None:
        self._update_sprites()
        own = self._own_active()
        rival = self._rival_active()
        if not own or not rival:
            for body in (self.move_body, self.switch_body, self.adv_body,
                         self.cover_body, self.mega_body):
                body.setText("Configura los Pokémon activos de ambos lados.")
            return

        self._fill_moves(own, rival)
        self._fill_switch(rival)
        self._fill_advantages(own, rival)
        self._fill_coverage(own, rival)
        self._fill_mega(own, rival)

    def _fill_moves(self, own: list[PokemonSet], rival: list[PokemonSet]) -> None:
        lines = []
        for own_set in own:
            analysis = battle_analyzer.analyze_moves(own_set, rival, self._db)
            if analysis is None:
                continue
            mon = self._db.get_pokemon(own_set.species)
            name = mon.display_name if mon else own_set.species
            best = analysis.top(2)
            if best:
                lines.append(f"{name}:")
                for i, rec in enumerate(best, 1):
                    lines.append(f"   {i}. {rec.move_name}  {rec.stars_text}")
            else:
                lines.append(f"{name}: sin movimientos definidos")
        title = "2 mejores ataques por Pokémon" if self._mode == MODE_DOUBLES else "Tus 2 mejores ataques"
        self.move_card.findChild(QLabel).setText(title)
        self.move_body.setText("\n".join(lines) or "—")

    def _fill_switch(self, rival: list[PokemonSet]) -> None:
        alive_picks = self._alive(self._picks)
        table = battle_analyzer.build_priority_table(alive_picks, rival, self._db)
        parts = []
        if table.best:
            parts.append(f"Mejor: {table.best.species}  {table.best.stars_text}")
        if table.worst and table.worst is not table.best:
            parts.append(f"Evita: {table.worst.species}  {table.worst.stars_text}")
        if self._mode == MODE_DOUBLES:
            pair = battle_analyzer.best_pair(alive_picks, rival, self._db)
            if pair:
                parts.append(f"Mejor pareja: {pair.species_a} + {pair.species_b}  {pair.stars_text}")
        if not alive_picks:
            parts = ["No te quedan Pokémon en pie."]
        self.switch_body.setText("\n".join(parts) or "—")

    def _speed_line(self, own: list[PokemonSet], rival: list[PokemonSet]) -> str:
        def spe(s: PokemonSet) -> Optional[int]:
            mon = self._db.get_pokemon(s.species)
            return mon.base_stats.velocidad if mon else None
        o = own[0]; r = rival[0]
        so, sr = spe(o), spe(r)
        if so is None or sr is None:
            return ""
        on = self._db.get_pokemon(o.species).display_name
        rn = self._db.get_pokemon(r.species).display_name
        if so > sr:
            return f"Velocidad: {on} ({so}) supera a {rn} ({sr}) — atacas primero."
        if so < sr:
            return f"Velocidad: {rn} ({sr}) supera a {on} ({so}) — el rival ataca primero."
        return f"Velocidad: empate ({so}) — decide la velocidad real (naturaleza/EVs/objeto)."

    def _fill_advantages(self, own: list[PokemonSet], rival: list[PokemonSet]) -> None:
        rival_types: list[str] = []
        for r in rival:
            mon = self._db.get_pokemon(r.species)
            if mon:
                rival_types.extend(mon.types)
        weaks = type_chart.weaknesses(rival_types)
        resists = type_chart.resistances(rival_types)
        lines = []
        if weaks:
            lines.append("Golpéalo con: " + ", ".join(list(weaks.keys())[:6]))
        if resists:
            lines.append("Resiste: " + ", ".join(list(resists.keys())[:6]))
        speed = self._speed_line(own, rival)
        if speed:
            lines.append(speed)
        # Aviso defensivo: con qué te golpea fuerte el rival (debilidades de tu activo).
        own_types: list[str] = []
        for o in own:
            mon = self._db.get_pokemon(o.species)
            if mon:
                own_types.extend(mon.types)
        my_weak = type_chart.weaknesses(own_types)
        if my_weak:
            lines.append("Te pega fuerte: " + ", ".join(list(my_weak.keys())[:6]))
        if self._mode == MODE_DOUBLES:
            threats = battle_analyzer.rival_threats_detail(rival, own, self._db)
            if threats:
                lines.append("Amenazas del rival:")
                for t, names in list(threats.items())[:5]:
                    lines.append(f"  · {t} → {', '.join(names)}")
        self.adv_body.setText("\n".join(lines) or "Sin ventajas de tipo claras.")

    def _fill_coverage(self, own: list[PokemonSet], rival: list[PokemonSet]) -> None:
        coverage = battle_analyzer.analyze_team_coverage(self._picks, self._db)
        lines = []
        if coverage.offensive_types_covered:
            top = list(coverage.offensive_types_covered.keys())[:8]
            lines.append("Ofensiva: " + ", ".join(top))
        if self._mode == MODE_DOUBLES and coverage.weakness_by_type:
            shared = {t: m for t, m in coverage.weakness_by_type.items() if len(m) >= 2}
            if shared:
                lines.append("Puntos débiles del equipo:")
                for t, names in list(shared.items())[:4]:
                    lines.append(f"  · {t} → {', '.join(names)}")
        self.cover_body.setText("\n".join(lines) or "—")

    def _matchup_score(self, own_set: PokemonSet, rival: list[PokemonSet]) -> float:
        m = battle_analyzer.evaluate_matchup(own_set, rival, self._db)
        return m.score if m else 0.0

    def _fill_mega(self, own: list[PokemonSet], rival: list[PokemonSet]) -> None:
        lines: list[str] = []
        # Aviso para cada Pokémon propio que pueda megaevolucionar.
        for combo, mega in zip(self._own_combos, self._own_mega):
            member = combo.currentData()
            if not member:
                continue
            form = self._mega_form_for(member)
            if not form:
                continue
            name = self._db.get_pokemon(member.species).display_name
            stone = self._db.mega_for_item(member.species, member.item)
            # Compara el enfrentamiento base vs mega contra el rival activo.
            base_score = self._matchup_score(member, rival)
            mega_score = self._matchup_score(replace(member, species=form), rival)
            if stone:
                req = f"lleva {member.item}"
            else:
                opts = self._db.mega_options(member.species)
                is_za = any(o["form"] == form and not o["stone"] for o in opts)
                req = "Z-A: sin objeto" if is_za else "requiere su Piedra Mega"
            verdict = ("conviene megaevolucionar ya" if mega_score > base_score + 0.01
                       else "mejor espera a un mejor momento" if mega_score < base_score - 0.01
                       else "indiferente en este enfrentamiento")
            if mega.isChecked():
                lines.append(f"{name} → {form} (activa): {req}.")
            else:
                lines.append(f"{name} puede megaevolucionar a {form} ({req}): {verdict}.")
            if stone is None and self._db.mega_for_item(member.species, member.item) is None and member.item:
                # Lleva un objeto que NO es su piedra.
                opts = self._db.mega_options(member.species)
                if opts and opts[0]["stone"]:
                    lines.append(f"   (para megaevolucionar, {name} debe llevar {opts[0]['stone']}).")
        # Aviso de megas del rival.
        rival_megas = []
        for combo, mega in zip(self._rival_combos, self._rival_mega):
            member = combo.currentData()
            form = self._mega_form_for(member) if member else ""
            if member and form:
                nm = self._db.get_pokemon(member.species).display_name
                rival_megas.append(f"{nm}→{form}" + (" (megaevolucionado)" if mega.isChecked() else ""))
        if rival_megas:
            lines.append("El rival puede megaevolucionar: " + ", ".join(rival_megas) + ".")
        if lines:
            lines.append("Regla: solo 1 megaevolución por equipo y combate; elige bien el turno.")
        self.mega_body.setText("\n".join(lines) or
                               "Ningún activo puede megaevolucionar (equipa una Piedra Mega o usa una especie con mega).")
