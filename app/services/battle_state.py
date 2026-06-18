"""Estado de combate en vivo: Pokémon debilitados y registro de quién derrotó a quién.

Es un estado de sesión (no se guarda en disco). Lo comparten el marcador
(``BattleTracker``) y la pantalla de combate (``BattleScreen``): el primero lo
edita y la segunda excluye del análisis a los Pokémon debilitados.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from app.models.pokemon_set import PokemonSet


class BattleState(QObject):
    """Marca qué Pokémon están debilitados y registra los derribos."""

    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._fainted: set[int] = set()          # id(PokemonSet) debilitados
        self._ko_by: dict[int, str] = {}         # id(set) -> nombre del que lo derrotó
        self.log: list[str] = []

    # --- Consultas ---------------------------------------------------------

    def is_fainted(self, pset: PokemonSet) -> bool:
        return id(pset) in self._fainted

    def alive(self, members: list[PokemonSet]) -> list[PokemonSet]:
        return [m for m in members if not m.is_empty and id(m) not in self._fainted]

    def count_alive(self, members: list[PokemonSet]) -> int:
        return len(self.alive(members))

    def ko_by(self, pset: PokemonSet) -> str:
        return self._ko_by.get(id(pset), "")

    # --- Mutación ----------------------------------------------------------

    def set_fainted(self, pset: PokemonSet, fainted: bool, name: str,
                    by: str = "") -> None:
        key = id(pset)
        if fainted:
            self._fainted.add(key)
            if by:
                self._ko_by[key] = by
                self.log.append(f"{name} fue debilitado por {by}.")
            else:
                self.log.append(f"{name} fue debilitado.")
        else:
            self._fainted.discard(key)
            self._ko_by.pop(key, None)
            self.log.append(f"{name} vuelve al combate.")
        self.changed.emit()

    def reset(self) -> None:
        self._fainted.clear()
        self._ko_by.clear()
        self.log.clear()
        self.changed.emit()
