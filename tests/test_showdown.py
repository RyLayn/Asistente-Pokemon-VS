"""Pruebas de importación/exportación en formato Showdown."""

from app.import_export import showdown

SAMPLE = """Dragonite @ Heavy-Duty Boots
Ability: Multiscale
Tera Type: Normal
EVs: 252 Atk / 4 Def / 252 Spe
Adamant Nature
- Extreme Speed
- Dragon Dance
- Earthquake
- Fire Punch

Garchomp @ Choice Scarf
Ability: Rough Skin
Tera Type: Ground
Jolly Nature
- Earthquake
- Dragon Claw
- Stone Edge
- Swords Dance
"""


def test_parse_team_count():
    sets = showdown.parse_team(SAMPLE)
    assert len(sets) == 2


def test_parse_header_species_and_item():
    sets = showdown.parse_team(SAMPLE)
    first = sets[0]
    assert first.species == "Dragonite"
    assert first.item == "Heavy-Duty Boots"


def test_parse_fields():
    first = showdown.parse_team(SAMPLE)[0]
    assert first.ability == "Multiscale"
    assert first.tera_type in ("Normal", "Normal")
    # La naturaleza en inglés se traduce a español.
    assert first.nature == "Firme"
    assert "Extreme Speed" in first.moves
    assert len([m for m in first.moves if m]) == 4


def test_export_roundtrip():
    sets = showdown.parse_team(SAMPLE)
    text = showdown.export_team(sets)
    reparsed = showdown.parse_team(text)
    assert len(reparsed) == 2
    assert reparsed[0].species == "Dragonite"


def test_round_trip_export_import_preserves_team():
    """Exportar y volver a importar reconstruye el mismo equipo."""
    from app.services.database_service import DatabaseService
    from app.services.team_service import TeamService
    from app.models.pokemon_set import PokemonSet

    db = DatabaseService()
    ts = TeamService(db)
    ts.user_team.members[0] = PokemonSet(
        species="Garchomp", level=50, nature="Firme", ability="Piel Tosca",
        item="Restos", tera_type="Acero",
        moves=["Terremoto", "Garra Dragón", "Abrecaminos", "Trompo Gélido"],
    )
    text = ts.export_showdown(ts.user_team)
    ts.import_showdown(text, as_enemy=False)
    m = ts.user_team.members[0]
    assert m.species == "Garchomp"
    assert m.level == 50
    assert m.nature == "Firme"
    assert m.ability == "Piel Tosca"
    assert m.tera_type == "Acero"
    assert "Abrecaminos" in m.moves and "Terremoto" in m.moves
