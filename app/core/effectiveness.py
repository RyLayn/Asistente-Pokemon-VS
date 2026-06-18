"""Cálculos de efectividad ofensiva: STAB, multiplicadores y valoración.

Este módulo es independiente de la interfaz y de los servicios de datos para
poder probarse de forma aislada. La arquitectura deja preparada la entrada de
modificadores adicionales (clima, terreno, estados, habilidades, objetos)
añadiendo factores al cálculo de ``effective_power`` sin alterar la API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from app.core import type_chart
from app.models.move import Move

STAB_MULTIPLIER = 1.5

# Mapa de multiplicador de tipo -> estrellas base (1..5) para movimientos.
_MOVE_STAR_BY_MULT: list[tuple[float, int]] = [
    (4.0, 5),
    (2.0, 4),
    (1.0, 3),
    (0.5, 2),
    (0.25, 1),
    (0.0, 1),
]

STAR_LABELS = {
    5: "Excelente",
    4: "Muy bueno",
    3: "Bueno",
    2: "Neutral",
    1: "Malo",
}


def stars_text(stars: int) -> str:
    """Cadena de estrellas (★) rellenando con vacías (☆) hasta 5."""
    stars = max(0, min(5, stars))
    return "★" * stars + "☆" * (5 - stars)


def has_stab(move_type: str, attacker_types: Iterable[str]) -> bool:
    """Indica si el movimiento recibe bonificación por tipo (STAB)."""
    return move_type in set(attacker_types)


def stab_multiplier(move_type: str, attacker_types: Iterable[str]) -> float:
    """Devuelve 1.5 si hay STAB, 1.0 en caso contrario."""
    return STAB_MULTIPLIER if has_stab(move_type, attacker_types) else 1.0


def type_effectiveness(move_type: str, defender_types: Iterable[str]) -> float:
    """Multiplicador de tipo del movimiento contra el defensor."""
    return type_chart.effectiveness(move_type, defender_types)


@dataclass(slots=True)
class MoveRating:
    """Resultado de valorar un movimiento contra un objetivo."""

    move_name: str
    move_type: str
    category: str
    stab: bool
    type_multiplier: float
    effective_power: float
    stars: int

    @property
    def label(self) -> str:
        return STAR_LABELS.get(self.stars, "Malo")

    @property
    def stars_text(self) -> str:
        return stars_text(self.stars)


def _stars_from_multiplier(multiplier: float) -> int:
    for threshold, stars in _MOVE_STAR_BY_MULT:
        if multiplier >= threshold:
            return stars
    return 1


def rate_move(
    move: Move,
    attacker_types: Sequence[str],
    defender_types: Sequence[str],
) -> MoveRating:
    """Valora un movimiento ofensivo contra un Pokémon defensor.

    La puntuación parte del multiplicador de tipo y recibe un empujón de +1
    estrella cuando hay STAB y la efectividad ya es neutra o superior.
    Los movimientos de estado se valoran como utilidad neutra (3★).
    """
    stab = has_stab(move.type, attacker_types)

    if not move.is_damaging:
        # Movimiento de estado: utilidad, efectividad no aplicable.
        return MoveRating(
            move_name=move.name, move_type=move.type, category=move.category,
            stab=False, type_multiplier=1.0, effective_power=0.0, stars=3,
        )

    mult = type_effectiveness(move.type, defender_types)
    stars = _stars_from_multiplier(mult)
    if stab and mult >= 1.0:
        stars = min(5, stars + 1)
    if mult == 0.0:
        stars = 1  # inmunidad: siempre malo

    # Potencia efectiva (preparada para más factores en el futuro).
    base_power = move.power if move.power > 0 else 60  # variable -> estimación
    effective_power = base_power * mult * stab_multiplier(move.type, attacker_types)

    return MoveRating(
        move_name=move.name, move_type=move.type, category=move.category,
        stab=stab, type_multiplier=mult, effective_power=effective_power,
        stars=stars,
    )
