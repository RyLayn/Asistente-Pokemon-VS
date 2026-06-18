"""Tabla de efectividades de tipos (18 tipos, mecánicas modernas Gen 6+).

Solo se almacenan los multiplicadores distintos de 1.0; cualquier
combinación ausente se interpreta como efectividad neutra (x1).
La arquitectura está pensada para ampliarse con climas, terrenos, estados,
habilidades y objetos sin reescribir el motor.
"""

from __future__ import annotations

from typing import Iterable

# Orden canónico de los 18 tipos, en español.
TYPES: tuple[str, ...] = (
    "Normal", "Fuego", "Agua", "Eléctrico", "Planta", "Hielo",
    "Lucha", "Veneno", "Tierra", "Volador", "Psíquico", "Bicho",
    "Roca", "Fantasma", "Dragón", "Siniestro", "Acero", "Hada",
)

# Multiplicadores ofensivos: TIPO_ATACANTE -> {TIPO_DEFENSOR: multiplicador}.
_CHART: dict[str, dict[str, float]] = {
    "Normal": {"Roca": 0.5, "Fantasma": 0.0, "Acero": 0.5},
    "Fuego": {"Fuego": 0.5, "Agua": 0.5, "Planta": 2.0, "Hielo": 2.0,
              "Bicho": 2.0, "Roca": 0.5, "Dragón": 0.5, "Acero": 2.0},
    "Agua": {"Fuego": 2.0, "Agua": 0.5, "Planta": 0.5, "Tierra": 2.0,
             "Roca": 2.0, "Dragón": 0.5},
    "Eléctrico": {"Agua": 2.0, "Eléctrico": 0.5, "Planta": 0.5,
                  "Tierra": 0.0, "Volador": 2.0, "Dragón": 0.5},
    "Planta": {"Fuego": 0.5, "Agua": 2.0, "Planta": 0.5, "Veneno": 0.5,
               "Tierra": 2.0, "Volador": 0.5, "Bicho": 0.5, "Roca": 2.0,
               "Dragón": 0.5, "Acero": 0.5},
    "Hielo": {"Fuego": 0.5, "Agua": 0.5, "Planta": 2.0, "Hielo": 0.5,
              "Tierra": 2.0, "Volador": 2.0, "Dragón": 2.0, "Acero": 0.5},
    "Lucha": {"Normal": 2.0, "Hielo": 2.0, "Veneno": 0.5, "Volador": 0.5,
              "Psíquico": 0.5, "Bicho": 0.5, "Roca": 2.0, "Fantasma": 0.0,
              "Siniestro": 2.0, "Acero": 2.0, "Hada": 0.5},
    "Veneno": {"Planta": 2.0, "Veneno": 0.5, "Tierra": 0.5, "Roca": 0.5,
               "Fantasma": 0.5, "Acero": 0.0, "Hada": 2.0},
    "Tierra": {"Fuego": 2.0, "Eléctrico": 2.0, "Planta": 0.5, "Veneno": 2.0,
               "Volador": 0.0, "Bicho": 0.5, "Roca": 2.0, "Acero": 2.0},
    "Volador": {"Eléctrico": 0.5, "Planta": 2.0, "Lucha": 2.0, "Bicho": 2.0,
                "Roca": 0.5, "Acero": 0.5},
    "Psíquico": {"Lucha": 2.0, "Veneno": 2.0, "Psíquico": 0.5,
                 "Siniestro": 0.0, "Acero": 0.5},
    "Bicho": {"Fuego": 0.5, "Planta": 2.0, "Lucha": 0.5, "Veneno": 0.5,
              "Volador": 0.5, "Psíquico": 2.0, "Fantasma": 0.5,
              "Siniestro": 2.0, "Acero": 0.5, "Hada": 0.5},
    "Roca": {"Fuego": 2.0, "Hielo": 2.0, "Lucha": 0.5, "Tierra": 0.5,
             "Volador": 2.0, "Bicho": 2.0, "Acero": 0.5},
    "Fantasma": {"Normal": 0.0, "Psíquico": 2.0, "Fantasma": 2.0,
                 "Siniestro": 0.5},
    "Dragón": {"Dragón": 2.0, "Acero": 0.5, "Hada": 0.0},
    "Siniestro": {"Lucha": 0.5, "Psíquico": 2.0, "Fantasma": 2.0,
                  "Siniestro": 0.5, "Hada": 0.5},
    "Acero": {"Fuego": 0.5, "Agua": 0.5, "Eléctrico": 0.5, "Hielo": 2.0,
              "Roca": 2.0, "Acero": 0.5, "Hada": 2.0},
    "Hada": {"Fuego": 0.5, "Lucha": 2.0, "Veneno": 0.5, "Dragón": 2.0,
             "Siniestro": 2.0, "Acero": 0.5},
}


def is_valid_type(type_name: str) -> bool:
    """Indica si ``type_name`` es un tipo reconocido."""
    return type_name in TYPES


def single_multiplier(attack_type: str, defend_type: str) -> float:
    """Multiplicador de un tipo atacante contra un único tipo defensor."""
    return _CHART.get(attack_type, {}).get(defend_type, 1.0)


def effectiveness(attack_type: str, defender_types: Iterable[str]) -> float:
    """Multiplicador total de un movimiento contra uno o dos tipos defensores.

    Args:
        attack_type: tipo del movimiento ofensivo.
        defender_types: tipos del Pokémon defensor (1 o 2).

    Returns:
        Producto de los multiplicadores (0, 0.25, 0.5, 1, 2 o 4).
    """
    multiplier = 1.0
    for defend_type in defender_types:
        multiplier *= single_multiplier(attack_type, defend_type)
    return multiplier


def defensive_profile(defender_types: Iterable[str]) -> dict[str, float]:
    """Multiplicador recibido por el defensor frente a *cada* tipo atacante.

    Útil para listar debilidades, resistencias e inmunidades de un Pokémon.
    """
    defender_types = list(defender_types)
    return {atk: effectiveness(atk, defender_types) for atk in TYPES}


def weaknesses(defender_types: Iterable[str]) -> dict[str, float]:
    """Tipos frente a los que el defensor recibe daño aumentado (>1)."""
    return {t: m for t, m in defensive_profile(defender_types).items() if m > 1.0}


def resistances(defender_types: Iterable[str]) -> dict[str, float]:
    """Tipos frente a los que el defensor recibe daño reducido (0<m<1)."""
    return {t: m for t, m in defensive_profile(defender_types).items()
            if 0.0 < m < 1.0}


def immunities(defender_types: Iterable[str]) -> list[str]:
    """Tipos frente a los que el defensor es inmune (x0)."""
    return [t for t, m in defensive_profile(defender_types).items() if m == 0.0]
