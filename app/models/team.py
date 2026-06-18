"""Modelo de equipo: hasta 6 configuraciones de Pokémon."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.config import TEAM_SIZE
from app.models.pokemon_set import PokemonSet


@dataclass(slots=True)
class Team:
    """Equipo del usuario o enemigo (máx. 6 Pokémon)."""

    name: str = "Nuevo equipo"
    members: list[PokemonSet] = field(default_factory=list)
    team_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    is_enemy: bool = False

    def __post_init__(self) -> None:
        members = list(self.members)[:TEAM_SIZE]
        while len(members) < TEAM_SIZE:
            members.append(PokemonSet())
        self.members = members

    @property
    def active_members(self) -> list[PokemonSet]:
        """Miembros que tienen una especie asignada."""
        return [m for m in self.members if not m.is_empty]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "team_id": self.team_id,
            "is_enemy": self.is_enemy,
            "members": [m.to_dict() for m in self.members],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Team":
        return cls(
            name=data.get("name", "Equipo"),
            team_id=data.get("team_id", uuid.uuid4().hex),
            is_enemy=bool(data.get("is_enemy", False)),
            members=[PokemonSet.from_dict(m) for m in data.get("members", [])],
        )

    def duplicate(self) -> "Team":
        """Crea una copia con nuevo identificador."""
        clone = Team.from_dict(self.to_dict())
        clone.team_id = uuid.uuid4().hex
        clone.name = f"{self.name} (copia)"
        return clone
