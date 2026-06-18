"""Analizador de combate.

Calcula qué Pokémon del equipo propio tiene ventaja frente a un rival activo,
valora los movimientos de un Pokémon concreto y analiza la cobertura del
equipo completo. Trabaja sobre un :class:`DataRepository`.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Optional, Sequence, Union

from app.core import type_chart
from app.core.effectiveness import (
    MoveRating,
    STAR_LABELS,
    rate_move,
    stars_text,
)
from app.core.repository import DataRepository
from app.models.move import Move
from app.models.pokemon import Pokemon
from app.models.pokemon_set import PokemonSet


# --- Valoración de enfrentamientos -----------------------------------------

@dataclass(slots=True)
class Matchup:
    """Resultado del enfrentamiento de un Pokémon propio contra el rival."""

    species: str
    types: list[str]
    offense_multiplier: float   # mejor multiplicador ofensivo logrado
    defense_multiplier: float   # peor multiplicador recibido (incoming)
    score: float                # ratio ofensiva/defensiva
    stars: int
    faster: Optional[bool] = None  # ¿es más rápido que el rival? (si se sabe)

    @property
    def label(self) -> str:
        return STAR_LABELS.get(self.stars, "Malo")

    @property
    def stars_text(self) -> str:
        return stars_text(self.stars)


def _best_offense(
    attacker: Pokemon,
    attacker_set: Optional[PokemonSet],
    defender_types: list[str],
    repo: DataRepository,
) -> float:
    """Mejor multiplicador de tipo que el atacante puede lograr.

    Usa los movimientos conocidos del set si existen; en su defecto recurre a
    los tipos del propio Pokémon (STAB) como cobertura mínima estimada.
    """
    candidate_types: list[str] = []

    if attacker_set is not None and attacker_set.known_moves:
        for move_name in attacker_set.known_moves:
            move = repo.get_move(move_name)
            if move is not None and move.is_damaging:
                candidate_types.append(move.type)

    if not candidate_types:
        candidate_types = list(attacker.types)

    if not candidate_types:
        return 1.0

    return max(type_chart.effectiveness(t, defender_types) for t in candidate_types)


def _worst_incoming(defender_types_self: list[str], rival_types: list[str]) -> float:
    """Peor multiplicador que el rival inflige al Pokémon propio."""
    if not rival_types:
        return 1.0
    return max(
        type_chart.effectiveness(rt, defender_types_self) for rt in rival_types
    )


def _score_to_stars(score: float) -> int:
    if score >= 4.0:
        return 5
    if score >= 2.0:
        return 4
    if score >= 1.0:
        return 3
    if score >= 0.5:
        return 2
    return 1


# Un "rival" puede ser un único Pokémon (individual) o varios activos (dobles).
RivalArg = Union[PokemonSet, Sequence[PokemonSet]]


def _rival_sets(rival: RivalArg) -> list[PokemonSet]:
    if isinstance(rival, PokemonSet):
        return [rival]
    return [r for r in rival if r is not None and not r.is_empty]


def evaluate_matchup(
    own_set: PokemonSet,
    rival: RivalArg,
    repo: DataRepository,
) -> Optional[Matchup]:
    """Evalúa un Pokémon propio frente a uno o varios rivales activos.

    La ofensiva es el mejor multiplicador que el propio logra contra *algún*
    rival; la defensa es el peor golpe que recibe de *cualquier* rival (caso
    peor, pensado para dobles donde ambos pueden atacar al mismo objetivo).
    """
    own = repo.get_pokemon(own_set.species)
    if own is None:
        return None
    rivals = _rival_sets(rival)
    rival_mons = [m for m in (repo.get_pokemon(r.species) for r in rivals) if m]
    if not rival_mons:
        return None

    offense = max(
        _best_offense(own, own_set, rm.types, repo) for rm in rival_mons
    )
    defense = max(_worst_incoming(own.types, rm.types) for rm in rival_mons)
    score = offense / max(defense, 0.25)
    stars = _score_to_stars(score)

    faster: Optional[bool] = None
    rival_speeds = [rm.base_stats.velocidad for rm in rival_mons if rm.base_stats.velocidad]
    if own.base_stats.velocidad and rival_speeds:
        faster = own.base_stats.velocidad >= max(rival_speeds)

    return Matchup(
        species=own.display_name,
        types=list(own.types),
        offense_multiplier=offense,
        defense_multiplier=defense,
        score=score,
        stars=stars,
        faster=faster,
    )


@dataclass(slots=True)
class PriorityTable:
    """Tabla de prioridad de cambios frente a un rival."""

    rival_species: str
    matchups: list[Matchup] = field(default_factory=list)

    @property
    def best(self) -> Optional[Matchup]:
        return self.matchups[0] if self.matchups else None

    @property
    def worst(self) -> Optional[Matchup]:
        return self.matchups[-1] if self.matchups else None


def build_priority_table(
    own_members: list[PokemonSet],
    rival: RivalArg,
    repo: DataRepository,
) -> PriorityTable:
    """Ordena el equipo propio de mejor a peor enfrentamiento contra el rival."""
    matchups: list[Matchup] = []
    for member in own_members:
        if member.is_empty:
            continue
        m = evaluate_matchup(member, rival, repo)
        if m is not None:
            matchups.append(m)
    matchups.sort(key=lambda mu: (mu.score, mu.offense_multiplier), reverse=True)

    rivals = _rival_sets(rival)
    names = []
    for r in rivals:
        mon = repo.get_pokemon(r.species)
        names.append(mon.display_name if mon else r.species)
    rival_name = " + ".join(names) if names else "—"
    return PriorityTable(rival_species=rival_name, matchups=matchups)


# --- Análisis de movimientos -----------------------------------------------

@dataclass(slots=True)
class MoveAnalysis:
    """Análisis de los movimientos de un Pokémon propio contra un rival."""

    species: str
    ratings: list[MoveRating] = field(default_factory=list)

    @property
    def recommended(self) -> Optional[MoveRating]:
        if not self.ratings:
            return None
        return max(self.ratings, key=lambda r: (r.stars, r.effective_power))

    def top(self, n: int = 2) -> list[MoveRating]:
        """Los ``n`` mejores movimientos contra el rival, de mejor a peor."""
        return sorted(
            self.ratings, key=lambda r: (r.stars, r.effective_power), reverse=True
        )[:n]


def analyze_moves(
    own_set: PokemonSet,
    rival: RivalArg,
    repo: DataRepository,
) -> Optional[MoveAnalysis]:
    """Valora cada movimiento del Pokémon propio contra el/los rival(es) activos.

    En dobles, cada movimiento se valora contra su *mejor* objetivo posible.
    """
    own = repo.get_pokemon(own_set.species)
    if own is None:
        return None
    rivals = _rival_sets(rival)
    rival_mons = [m for m in (repo.get_pokemon(r.species) for r in rivals) if m]
    if not rival_mons:
        return None

    ratings: list[MoveRating] = []
    for move_name in own_set.moves:
        if not move_name:
            continue
        move = repo.get_move(move_name)
        if move is None:
            move = Move(name=move_name, type="Normal", category="Estado")
        # Mejor objetivo: el que da más estrellas (y, a igualdad, más potencia).
        best = max(
            (rate_move(move, own.types, rm.types) for rm in rival_mons),
            key=lambda r: (r.stars, r.effective_power),
        )
        ratings.append(best)

    return MoveAnalysis(species=own.display_name, ratings=ratings)


# --- Análisis específico de dobles -----------------------------------------

@dataclass(slots=True)
class PairSuggestion:
    """Mejor pareja del equipo propio frente a los rivales activos."""

    species_a: str
    species_b: str
    score: float
    stars: int

    @property
    def stars_text(self) -> str:
        return stars_text(self.stars)

    @property
    def label(self) -> str:
        return STAR_LABELS.get(self.stars, "Malo")


def best_pair(
    own_members: list[PokemonSet],
    rival: RivalArg,
    repo: DataRepository,
) -> Optional[PairSuggestion]:
    """Encuentra la mejor pareja propia contra los rivales activos (dobles)."""
    active = [m for m in own_members if not m.is_empty]
    if len(active) < 2:
        return None

    best: Optional[PairSuggestion] = None
    for a, b in itertools.combinations(active, 2):
        ma = evaluate_matchup(a, rival, repo)
        mb = evaluate_matchup(b, rival, repo)
        if ma is None or mb is None:
            continue
        combined = ma.score + mb.score
        if best is None or combined > best.score:
            stars = _score_to_stars((ma.score + mb.score) / 2)
            best = PairSuggestion(
                species_a=ma.species,
                species_b=mb.species,
                score=combined,
                stars=stars,
            )
    return best


def rival_threats(
    rival: RivalArg,
    own_active: list[PokemonSet],
    repo: DataRepository,
) -> dict[str, int]:
    """Tipos de los rivales activos frente a los que mis activos son débiles.

    Devuelve un mapa tipo -> número de mis Pokémon activos que lo sufren (>1x).
    """
    rivals = _rival_sets(rival)
    rival_mons = [m for m in (repo.get_pokemon(r.species) for r in rivals) if m]
    own_mons = [m for m in (repo.get_pokemon(o.species) for o in own_active if not o.is_empty) if m]
    if not rival_mons or not own_mons:
        return {}

    rival_types: set[str] = set()
    for rm in rival_mons:
        rival_types.update(rm.types)

    threats: dict[str, int] = {}
    for rt in rival_types:
        count = sum(
            1 for om in own_mons
            if type_chart.effectiveness(rt, om.types) > 1.0
        )
        if count:
            threats[rt] = count
    return dict(sorted(threats.items(), key=lambda kv: kv[1], reverse=True))


def rival_threats_detail(
    rival: RivalArg,
    own_active: list[PokemonSet],
    repo: DataRepository,
) -> dict[str, list[str]]:
    """Como :func:`rival_threats`, pero devuelve los nombres de los Pokémon
    propios débiles a cada tipo amenazante del rival."""
    rivals = _rival_sets(rival)
    rival_mons = [m for m in (repo.get_pokemon(r.species) for r in rivals) if m]
    own_pairs = [(o, repo.get_pokemon(o.species)) for o in own_active if not o.is_empty]
    own_pairs = [(o, m) for o, m in own_pairs if m]
    if not rival_mons or not own_pairs:
        return {}

    rival_types: set[str] = set()
    for rm in rival_mons:
        rival_types.update(rm.types)

    detail: dict[str, list[str]] = {}
    for rt in rival_types:
        names = [m.display_name for _o, m in own_pairs
                 if type_chart.effectiveness(rt, m.types) > 1.0]
        if names:
            detail[rt] = names
    return dict(sorted(detail.items(), key=lambda kv: len(kv[1]), reverse=True))


# --- Cobertura del equipo ---------------------------------------------------

@dataclass(slots=True)
class TeamCoverage:
    """Análisis de cobertura ofensiva y defensiva del equipo completo."""

    offensive_types_covered: dict[str, int]   # tipo super-eficaz -> nº de mons
    common_weaknesses: dict[str, int]          # tipo amenaza -> nº de mons débiles
    vulnerable_members: list[str]              # mons con muchas debilidades
    best_coverage_members: list[str]           # mons que aportan mejor cobertura
    offensive_by_type: dict[str, list[str]] = field(default_factory=dict)   # tipo -> mons que lo cubren
    weakness_by_type: dict[str, list[str]] = field(default_factory=dict)    # tipo -> mons débiles
    member_weakness_detail: dict[str, list[str]] = field(default_factory=dict)  # mon -> tipos débiles


def analyze_team_coverage(
    members: list[PokemonSet],
    repo: DataRepository,
) -> TeamCoverage:
    """Calcula cobertura ofensiva, amenazas comunes y vulnerabilidades."""
    offensive: dict[str, int] = {t: 0 for t in type_chart.TYPES}
    weakness_count: dict[str, int] = {t: 0 for t in type_chart.TYPES}
    member_weaknesses: dict[str, int] = {}
    member_coverage: dict[str, int] = {}
    offensive_by_type: dict[str, list[str]] = {t: [] for t in type_chart.TYPES}
    weakness_by_type: dict[str, list[str]] = {t: [] for t in type_chart.TYPES}
    member_weakness_detail: dict[str, list[str]] = {}

    for member in members:
        if member.is_empty:
            continue
        mon = repo.get_pokemon(member.species)
        if mon is None:
            continue

        # Cobertura ofensiva: tipos contra los que el equipo pega super-eficaz.
        atk_types: list[str] = []
        for move_name in member.known_moves:
            move = repo.get_move(move_name)
            if move is not None and move.is_damaging:
                atk_types.append(move.type)
        if not atk_types:
            atk_types = list(mon.types)

        super_eff = set()
        for atk in atk_types:
            for defend in type_chart.TYPES:
                if type_chart.single_multiplier(atk, defend) > 1.0:
                    super_eff.add(defend)
        for t in super_eff:
            offensive[t] += 1
            offensive_by_type[t].append(mon.display_name)
        member_coverage[mon.display_name] = len(super_eff)

        # Debilidades defensivas.
        weaks = type_chart.weaknesses(mon.types)
        for t in weaks:
            weakness_count[t] += 1
            weakness_by_type[t].append(mon.display_name)
        member_weaknesses[mon.display_name] = len(weaks)
        member_weakness_detail[mon.display_name] = list(weaks.keys())

    offensive_covered = {t: c for t, c in offensive.items() if c > 0}
    threats = {t: c for t, c in weakness_count.items() if c >= 2}
    offensive_by_type = {t: m for t, m in offensive_by_type.items() if m}
    weakness_by_type = {t: m for t, m in weakness_by_type.items() if m}

    vulnerable = sorted(
        member_weaknesses, key=lambda n: member_weaknesses[n], reverse=True
    )[:3]
    best = sorted(
        member_coverage, key=lambda n: member_coverage[n], reverse=True
    )[:3]

    return TeamCoverage(
        offensive_types_covered=dict(sorted(offensive_covered.items(), key=lambda kv: kv[1], reverse=True)),
        common_weaknesses=dict(sorted(threats.items(), key=lambda kv: kv[1], reverse=True)),
        vulnerable_members=vulnerable,
        best_coverage_members=best,
        offensive_by_type=offensive_by_type,
        weakness_by_type=weakness_by_type,
        member_weakness_detail=member_weakness_detail,
    )
