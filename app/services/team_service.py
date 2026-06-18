"""Servicio de gestión de equipos.

Encapsula el equipo del usuario y el equipo enemigo en memoria, su persistencia
en disco (JSON) y la importación/exportación en formato Showdown, resolviendo
los nombres importados contra la base de datos en español.
"""

from __future__ import annotations

from pathlib import Path

from app.import_export import showdown, team_io
from app.models.pokemon_set import PokemonSet
from app.models.team import Team
from app.services.database_service import DatabaseService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TeamService:
    """Operaciones de alto nivel sobre equipos."""

    def __init__(self, db: DatabaseService) -> None:
        self.db = db
        self.user_team = Team(name="Mi equipo")
        self.enemy_team = Team(name="Equipo rival", is_enemy=True)

    # --- Persistencia ------------------------------------------------------

    def save(self, team: Team) -> Path:
        return team_io.save_team(team)

    def load_all(self) -> list[Team]:
        return team_io.load_all_teams()

    def delete(self, team_id: str) -> bool:
        return team_io.delete_team(team_id)

    def duplicate(self, team: Team) -> Team:
        clone = team.duplicate()
        team_io.save_team(clone)
        return clone

    # --- Showdown ----------------------------------------------------------

    def _resolve_set(self, pset: PokemonSet) -> PokemonSet:
        """Traduce los nombres de un set importado al español de la BD."""
        pset.species = self.db.resolve_species(pset.species)
        pset.ability = self.db.resolve_ability(pset.ability) if pset.ability else ""
        pset.item = self.db.resolve_item(pset.item) if pset.item else ""
        pset.moves = [self.db.resolve_move(m) if m else "" for m in pset.moves]
        return pset

    def import_showdown(self, text: str, as_enemy: bool = False) -> Team:
        """Importa un equipo en formato Showdown y lo deja como activo."""
        sets = [self._resolve_set(s) for s in showdown.parse_team(text)]
        team = Team(
            name="Equipo importado",
            members=sets,
            is_enemy=as_enemy,
        )
        if as_enemy:
            self.enemy_team = team
        else:
            self.user_team = team
        logger.info("Importados %d Pokémon (enemigo=%s)", len(sets), as_enemy)
        return team

    def export_showdown(self, team: Team) -> str:
        """Exporta un equipo al formato Showdown."""
        return showdown.export_team(team.members)
