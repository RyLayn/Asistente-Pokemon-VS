"""Pruebas de la valoración de movimientos (estrellas y STAB)."""

from app.core.effectiveness import rate_move
from app.models.move import Move


def test_stab_boost_super_effective():
    # Trompo Gélido (Hielo) de un Hielo contra Dragón/Tierra: x4 + STAB -> 5★.
    move = Move(name="Trompo Gélido", type="Hielo", category="Físico", power=80)
    rating = rate_move(move, attacker_types=["Hielo"], defender_types=["Dragón", "Tierra"])
    assert rating.type_multiplier == 4.0
    assert rating.stab is True
    assert rating.stars == 5


def test_neutral_move_three_stars():
    move = Move(name="Terremoto", type="Tierra", category="Físico", power=100)
    rating = rate_move(move, attacker_types=["Agua"], defender_types=["Normal"])
    assert rating.type_multiplier == 1.0
    assert rating.stars == 3


def test_immune_move_one_star():
    move = Move(name="Terremoto", type="Tierra", category="Físico", power=100)
    rating = rate_move(move, attacker_types=["Tierra"], defender_types=["Volador"])
    assert rating.type_multiplier == 0.0
    assert rating.stars == 1


def test_status_move_is_neutral_utility():
    move = Move(name="Tóxico", type="Veneno", category="Estado", power=0)
    rating = rate_move(move, attacker_types=["Veneno"], defender_types=["Agua"])
    assert rating.stars == 3
    assert rating.stab is False
