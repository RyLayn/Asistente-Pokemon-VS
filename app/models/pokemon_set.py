"""Configuración concreta de un Pokémon dentro de un equipo (set)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.config import MOVES_PER_POKEMON


@dataclass(slots=True)
class PokemonSet:
    """Pokémon configurado por el usuario para un equipo.

    Para el equipo enemigo basta con ``species``; el resto de campos pueden
    quedar como desconocidos (cadena vacía), y el motor asumirá información
    incompleta.
    """

    species: str = ""           # nombre de la especie (clave de la Pokédex)
    nickname: str = ""
    level: int = 50
    nature: str = "Seria"
    ability: str = ""
    item: str = ""
    tera_type: str = ""
    moves: list[str] = field(default_factory=lambda: [""] * MOVES_PER_POKEMON)

    def __post_init__(self) -> None:
        # Garantiza siempre exactamente MOVES_PER_POKEMON ranuras de movimiento.
        moves = list(self.moves)[:MOVES_PER_POKEMON]
        while len(moves) < MOVES_PER_POKEMON:
            moves.append("")
        self.moves = moves

    @property
    def is_empty(self) -> bool:
        return not self.species

    @property
    def known_moves(self) -> list[str]:
        """Movimientos no vacíos."""
        return [m for m in self.moves if m]

    def to_dict(self) -> dict:
        return {
            "species": self.species,
            "nickname": self.nickname,
            "level": self.level,
            "nature": self.nature,
            "ability": self.ability,
            "item": self.item,
            "tera_type": self.tera_type,
            "moves": list(self.moves),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PokemonSet":
        return cls(
            species=data.get("species", ""),
            nickname=data.get("nickname", ""),
            level=int(data.get("level", 50)),
            nature=data.get("nature", "Seria"),
            ability=data.get("ability", ""),
            item=data.get("item", ""),
            tera_type=data.get("tera_type", ""),
            moves=list(data.get("moves", [])),
        )
