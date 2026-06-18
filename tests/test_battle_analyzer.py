"""Pruebas del analizador de combate con datos semilla reales."""

from app.core import battle_analyzer
from app.models.pokemon_set import PokemonSet
from app.services.database_service import DatabaseService


def _db() -> DatabaseService:
    return DatabaseService()


def test_priority_table_orders_by_advantage():
    db = _db()
    own = [
        PokemonSet(species="Baxcalibur", moves=["Trompo Gélido", "Garra Dragón", "Terremoto", "Esquirla Helada"]),
        PokemonSet(species="Dragonite"),
    ]
    rival = PokemonSet(species="Garchomp")
    table = battle_analyzer.build_priority_table(own, rival, db)
    assert table.matchups, "Debe haber enfrentamientos"
    # Baxcalibur (Hielo) tiene ventaja clara sobre Garchomp (Dragón/Tierra).
    assert table.best is not None
    assert "Baxcalibur" in table.best.species


def test_move_analysis_recommends_ice():
    db = _db()
    own = PokemonSet(
        species="Baxcalibur",
        moves=["Trompo Gélido", "Garra Dragón", "Terremoto", "Esquirla Helada"],
    )
    rival = PokemonSet(species="Garchomp")
    analysis = battle_analyzer.analyze_moves(own, rival, db)
    assert analysis is not None
    rec = analysis.recommended
    assert rec is not None
    # El ataque recomendado debe ser de tipo Hielo (x4 contra Garchomp).
    assert rec.move_type == "Hielo"
    assert rec.stars == 5


def test_team_coverage_runs():
    db = _db()
    members = [
        PokemonSet(species="Garchomp"),
        PokemonSet(species="Corviknight"),
        PokemonSet(species="Toxapex"),
    ]
    coverage = battle_analyzer.analyze_team_coverage(members, db)
    assert isinstance(coverage.offensive_types_covered, dict)
    assert coverage.vulnerable_members  # algún miembro listado


def test_multi_target_priority_doubles():
    """En dobles, la prioridad considera dos rivales activos a la vez."""
    db = _db()
    own = [
        PokemonSet(species="Baxcalibur", moves=["Trompo Gélido", "Garra Dragón", "Terremoto", "Esquirla Helada"]),
        PokemonSet(species="Corviknight"),
        PokemonSet(species="Heatran"),
    ]
    rivals = [PokemonSet(species="Garchomp"), PokemonSet(species="Dragonite")]
    table = battle_analyzer.build_priority_table(own, rivals, db)
    assert table.matchups
    assert "+" in table.rival_species  # nombre combinado de ambos rivales


def test_best_pair_returns_two_distinct():
    db = _db()
    own = [
        PokemonSet(species="Baxcalibur", moves=["Trompo Gélido", "Garra Dragón", "", ""]),
        PokemonSet(species="Corviknight"),
        PokemonSet(species="Heatran"),
        PokemonSet(species="Toxapex"),
    ]
    rivals = [PokemonSet(species="Garchomp"), PokemonSet(species="Dragonite")]
    pair = battle_analyzer.best_pair(own, rivals, db)
    assert pair is not None
    assert pair.species_a != pair.species_b


def test_rival_threats_counts_weak_actives():
    db = _db()
    rivals = [PokemonSet(species="Gardevoir")]  # Hada/Psíquico
    own_active = [PokemonSet(species="Baxcalibur"), PokemonSet(species="Kingambit")]
    threats = battle_analyzer.rival_threats(rivals, own_active, db)
    assert isinstance(threats, dict)
    # Hada amenaza a Baxcalibur (Dragón/Hielo) y a Kingambit (Siniestro/Acero).
    assert threats.get("Hada", 0) >= 1
