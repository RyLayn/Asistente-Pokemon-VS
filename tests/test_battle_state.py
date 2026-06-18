"""Pruebas del estado de combate en vivo (debilitados y derribos)."""

from app.models.pokemon_set import PokemonSet
from app.services.battle_state import BattleState


def test_fainted_tracking_and_counts():
    state = BattleState()
    a = PokemonSet(species="Charizard")
    b = PokemonSet(species="Garchomp")
    c = PokemonSet(species="Lucario")
    team = [a, b, c]
    assert state.count_alive(team) == 3
    state.set_fainted(a, True, "Charizard", by="Tyranitar")
    assert state.is_fainted(a)
    assert state.count_alive(team) == 2
    assert state.alive(team) == [b, c]
    assert state.ko_by(a) == "Tyranitar"
    assert any("Charizard" in line and "Tyranitar" in line for line in state.log)


def test_revive_and_reset():
    state = BattleState()
    a = PokemonSet(species="Pikachu")
    state.set_fainted(a, True, "Pikachu")
    state.set_fainted(a, False, "Pikachu")
    assert not state.is_fainted(a)
    state.set_fainted(a, True, "Pikachu")
    state.reset()
    assert not state.is_fainted(a)
    assert state.log == []
