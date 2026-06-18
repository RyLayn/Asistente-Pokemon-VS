"""Modelo de habilidad de un Pokémon."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Ability:
    """Habilidad de un Pokémon."""

    name: str
    description: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "description": self.description}

    @classmethod
    def from_dict(cls, data: dict) -> "Ability":
        return cls(name=data["name"], description=data.get("description", ""))
