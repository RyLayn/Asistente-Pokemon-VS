"""Protocolo de acceso a datos usado por el motor de análisis.

Define la interfaz mínima que el analizador de combate necesita, sin acoplarse
a una implementación concreta (SQLite, JSON, mock de tests...).
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from app.models.move import Move
from app.models.pokemon import Pokemon


@runtime_checkable
class DataRepository(Protocol):
    """Fuente de datos de Pokémon y movimientos."""

    def get_pokemon(self, name: str) -> Optional[Pokemon]:
        """Devuelve la especie por nombre (o forma) o ``None``."""
        ...

    def get_move(self, name: str) -> Optional[Move]:
        """Devuelve un movimiento por nombre o ``None``."""
        ...
