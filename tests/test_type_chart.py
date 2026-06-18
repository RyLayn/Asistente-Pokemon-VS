"""Pruebas de la tabla de tipos."""

from app.core import type_chart


def test_all_types_present():
    assert len(type_chart.TYPES) == 18
    assert "Hada" in type_chart.TYPES
    assert "Siniestro" in type_chart.TYPES


def test_single_super_effective():
    # Agua es super-eficaz contra Fuego.
    assert type_chart.single_multiplier("Agua", "Fuego") == 2.0


def test_single_not_very_effective():
    # Fuego es poco eficaz contra Agua.
    assert type_chart.single_multiplier("Fuego", "Agua") == 0.5


def test_immunity():
    # Normal no afecta a Fantasma.
    assert type_chart.single_multiplier("Normal", "Fantasma") == 0.0
    # Tierra no afecta a Volador.
    assert type_chart.single_multiplier("Tierra", "Volador") == 0.0


def test_dual_type_quad_weakness():
    # Hielo contra Dragón/Tierra (Garchomp) = x4.
    assert type_chart.effectiveness("Hielo", ["Dragón", "Tierra"]) == 4.0


def test_dual_type_cancel():
    # Planta contra Agua x2 pero Tierra/Volador... usamos un caso neto.
    # Fuego contra Bicho/Acero = x2 * x2 = x4.
    assert type_chart.effectiveness("Fuego", ["Bicho", "Acero"]) == 4.0


def test_weaknesses_and_immunities_helpers():
    weaks = type_chart.weaknesses(["Dragón", "Tierra"])
    assert "Hielo" in weaks and weaks["Hielo"] == 4.0
    immunities = type_chart.immunities(["Dragón", "Tierra"])
    assert "Eléctrico" in immunities
