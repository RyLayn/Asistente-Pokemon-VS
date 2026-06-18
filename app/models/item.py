"""Modelo de objeto equipable."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Item:
    """Objeto equipable."""

    name: str
    description: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "description": self.description}

    @classmethod
    def from_dict(cls, data: dict) -> "Item":
        return cls(name=data["name"], description=data.get("description", ""))
