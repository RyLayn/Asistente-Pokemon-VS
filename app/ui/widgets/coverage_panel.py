"""Panel de cobertura del equipo, explicado al detalle.

Pensado para alguien que está aprendiendo: no solo dice "Roca (3)", sino
exactamente qué Pokémon están afectados y qué significa cada apartado.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core import battle_analyzer
from app.models.team import Team
from app.services.database_service import DatabaseService


def _card(title: str, explanation: str) -> tuple[QFrame, QLabel]:
    card = QFrame()
    card.setObjectName("Card")
    lay = QVBoxLayout(card)
    lay.setContentsMargins(16, 14, 16, 14)
    lay.setSpacing(6)
    t = QLabel(title)
    t.setObjectName("SectionTitle")
    lay.addWidget(t)
    exp = QLabel(explanation)
    exp.setObjectName("Subtitle")
    exp.setWordWrap(True)
    lay.addWidget(exp)
    body = QLabel("—")
    body.setObjectName("CardBody")
    body.setWordWrap(True)
    body.setTextFormat(Qt.RichText)
    lay.addWidget(body)
    return card, body


class CoveragePanel(QWidget):
    """Análisis agregado y detallado de la cobertura del equipo."""

    def __init__(self, db: DatabaseService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db = db
        self._team = Team(name="Mi equipo")
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)

        header = QLabel("Cobertura del equipo")
        header.setObjectName("Title")
        outer.addWidget(header)
        subtitle = QLabel("Fortalezas y puntos débiles de tu equipo, explicados.")
        subtitle.setObjectName("Subtitle")
        outer.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        container = QWidget()
        col = QVBoxLayout(container)
        col.setContentsMargins(0, 6, 8, 0)
        col.setSpacing(12)

        self.offense_card, self.offense_body = _card(
            "Cobertura ofensiva",
            "Tipos a los que tu equipo puede golpear con daño aumentado (super eficaz), "
            "y qué Pokémon lo consiguen.",
        )
        self.threats_card, self.threats_body = _card(
            "Amenazas del equipo",
            "Tipos de ataque que hacen daño aumentado a VARIOS de tus Pokémon. "
            "Ojo con los rivales de estos tipos.",
        )
        self.weak_card, self.weak_body = _card(
            "Debilidades de cada Pokémon",
            "A qué tipos es débil cada miembro del equipo.",
        )
        self.summary_card, self.summary_body = _card(
            "Resumen",
            "Pokémon más expuestos y los que más cobertura aportan.",
        )
        for c in (self.offense_card, self.threats_card, self.weak_card, self.summary_card):
            col.addWidget(c)
        col.addStretch(1)
        scroll.setWidget(container)
        outer.addWidget(scroll, 1)

    def set_team(self, team: Team) -> None:
        self._team = team
        self.refresh()

    def refresh(self) -> None:
        cov = battle_analyzer.analyze_team_coverage(self._team.members, self._db)

        # Ofensiva: tipo -> quiénes.
        if cov.offensive_by_type:
            lines = []
            for t, mons in sorted(cov.offensive_by_type.items(),
                                  key=lambda kv: len(kv[1]), reverse=True):
                lines.append(f"<b>{t}</b> ({len(mons)}): {', '.join(mons)}")
            self.offense_body.setText("<br>".join(lines))
        else:
            self.offense_body.setText("Añade movimientos o Pokémon para calcular la cobertura.")

        # Amenazas: tipo con ≥2 débiles -> quiénes.
        threats = {t: mons for t, mons in cov.weakness_by_type.items() if len(mons) >= 2}
        if threats:
            lines = []
            for t, mons in sorted(threats.items(), key=lambda kv: len(kv[1]), reverse=True):
                lines.append(f"<b>{t}</b> golpea a {len(mons)}: {', '.join(mons)}")
            self.threats_body.setText("<br>".join(lines))
        else:
            self.threats_body.setText("Ningún tipo amenaza a dos o más de tus Pokémon a la vez. ¡Buen equilibrio!")

        # Debilidades por Pokémon.
        if cov.member_weakness_detail:
            lines = []
            for mon, weaks in cov.member_weakness_detail.items():
                lines.append(f"<b>{mon}</b>: {', '.join(weaks) if weaks else 'sin debilidades de tipo'}")
            self.weak_body.setText("<br>".join(lines))
        else:
            self.weak_body.setText("—")

        # Resumen.
        parts = []
        if cov.vulnerable_members:
            parts.append("Más expuestos: " + ", ".join(cov.vulnerable_members))
        if cov.best_coverage_members:
            parts.append("Mejor cobertura: " + ", ".join(cov.best_coverage_members))
        self.summary_body.setText("<br>".join(parts) or "—")
