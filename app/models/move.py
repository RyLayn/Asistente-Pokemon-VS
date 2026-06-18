"""Modelo de datos de un movimiento."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Move:
    """Representa un movimiento de combate.

    Attributes:
        name: nombre del movimiento.
        type: tipo (uno de los 18 tipos).
        category: "Físico", "Especial" o "Estado".
        power: potencia base (0 si es de estado o variable).
        accuracy: precisión 0-100 (0 = no falla / sin precisión).
        pp: puntos de poder.
        priority: prioridad del movimiento (-7..+5).
        effect: descripción breve del efecto.
    """

    name: str
    type: str
    category: str = "Físico"
    power: int = 0
    accuracy: int = 100
    pp: int = 0
    priority: int = 0
    effect: str = ""

    @property
    def is_damaging(self) -> bool:
        """True si el movimiento inflige daño (no es de estado)."""
        return self.category in ("Físico", "Especial")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "category": self.category,
            "power": self.power,
            "accuracy": self.accuracy,
            "pp": self.pp,
            "priority": self.priority,
            "effect": self.effect,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Move":
        return cls(
            name=data["name"],
            type=data.get("type", "Normal"),
            category=data.get("category", "Físico"),
            power=int(data.get("power", 0) or 0),
            accuracy=int(data.get("accuracy", 100) or 0),
            pp=int(data.get("pp", 0) or 0),
            priority=int(data.get("priority", 0) or 0),
            effect=data.get("effect", ""),
        )


def empty_move(name: str = "") -> Move:
    """Crea un movimiento vacío como marcador de posición."""
    return Move(name=name, type="Normal", category="Estado")
