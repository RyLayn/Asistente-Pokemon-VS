"""Modelo de una especie de Pokémon (datos de la Pokédex)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class BaseStats:
    """Estadísticas base de una especie."""

    ps: int = 0
    ataque: int = 0
    defensa: int = 0
    ataque_especial: int = 0
    defensa_especial: int = 0
    velocidad: int = 0

    @property
    def total(self) -> int:
        return (self.ps + self.ataque + self.defensa + self.ataque_especial
                + self.defensa_especial + self.velocidad)

    def to_dict(self) -> dict:
        return {
            "ps": self.ps, "ataque": self.ataque, "defensa": self.defensa,
            "ataque_especial": self.ataque_especial,
            "defensa_especial": self.defensa_especial,
            "velocidad": self.velocidad,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BaseStats":
        return cls(
            ps=int(data.get("ps", 0)),
            ataque=int(data.get("ataque", 0)),
            defensa=int(data.get("defensa", 0)),
            ataque_especial=int(data.get("ataque_especial", 0)),
            defensa_especial=int(data.get("defensa_especial", 0)),
            velocidad=int(data.get("velocidad", 0)),
        )


@dataclass(slots=True)
class Pokemon:
    """Especie de Pokémon con todos sus datos de Pokédex.

    Se contemplan formas regionales, megaevoluciones y formas alternativas
    mediante el campo ``form`` y un ``dex_number`` compartido por especie.
    """

    name: str
    dex_number: int
    types: list[str] = field(default_factory=list)
    base_stats: BaseStats = field(default_factory=BaseStats)
    abilities: list[str] = field(default_factory=list)
    learnable_moves: list[str] = field(default_factory=list)
    form: str = ""           # "", "Alola", "Galar", "Hisui", "Mega", "Paldea"...
    sprite_key: str = ""     # identificador para el sprite local
    generation: int = 0

    @property
    def display_name(self) -> str:
        """Nombre para mostrar incluyendo la forma si la hay."""
        if self.form:
            return f"{self.name} ({self.form})"
        return self.name

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "dex_number": self.dex_number,
            "types": list(self.types),
            "base_stats": self.base_stats.to_dict(),
            "abilities": list(self.abilities),
            "learnable_moves": list(self.learnable_moves),
            "form": self.form,
            "sprite_key": self.sprite_key,
            "generation": self.generation,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Pokemon":
        return cls(
            name=data["name"],
            dex_number=int(data.get("dex_number", 0)),
            types=list(data.get("types", [])),
            base_stats=BaseStats.from_dict(data.get("base_stats", {})),
            abilities=list(data.get("abilities", [])),
            learnable_moves=list(data.get("learnable_moves", [])),
            form=data.get("form", ""),
            sprite_key=data.get("sprite_key", str(data.get("dex_number", 0))),
            generation=int(data.get("generation", 0)),
        )
