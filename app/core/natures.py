"""Naturalezas de Pokémon y sus modificadores de estadística (+10% / -10%).

Nombres en la localización española oficial. Las naturalezas neutras no
modifican ninguna estadística.
"""

from __future__ import annotations

# Estadísticas afectables por la naturaleza (la PS nunca se ve afectada).
STATS = ("ataque", "defensa", "ataque_especial", "defensa_especial", "velocidad")

# naturaleza -> (estadística que sube, estadística que baja).
# Las neutras tienen (None, None).
NATURES: dict[str, tuple[str | None, str | None]] = {
    # Neutras
    "Fuerte": (None, None),
    "Dócil": (None, None),
    "Seria": (None, None),
    "Tímida": (None, None),
    "Rara": (None, None),
    # +Ataque
    "Huraña": ("ataque", "defensa"),
    "Audaz": ("ataque", "velocidad"),
    "Firme": ("ataque", "ataque_especial"),
    "Pícara": ("ataque", "defensa_especial"),
    # +Defensa
    "Osada": ("defensa", "ataque"),
    "Plácida": ("defensa", "velocidad"),
    "Agitada": ("defensa", "ataque_especial"),
    "Floja": ("defensa", "defensa_especial"),
    # +Velocidad
    "Miedosa": ("velocidad", "ataque"),
    "Activa": ("velocidad", "defensa"),
    "Alegre": ("velocidad", "ataque_especial"),
    "Ingenua": ("velocidad", "defensa_especial"),
    # +Ataque especial
    "Modesta": ("ataque_especial", "ataque"),
    "Afable": ("ataque_especial", "defensa"),
    "Mansa": ("ataque_especial", "velocidad"),
    "Alocada": ("ataque_especial", "defensa_especial"),
    # +Defensa especial
    "Serena": ("defensa_especial", "ataque"),
    "Amable": ("defensa_especial", "defensa"),
    "Grosera": ("defensa_especial", "velocidad"),
    "Cauta": ("defensa_especial", "ataque_especial"),
}


def nature_multiplier(nature: str, stat: str) -> float:
    """Multiplicador (1.1, 0.9 o 1.0) de una naturaleza sobre una estadística."""
    boost, drop = NATURES.get(nature, (None, None))
    if boost == drop:  # neutra
        return 1.0
    if stat == boost:
        return 1.1
    if stat == drop:
        return 0.9
    return 1.0


def all_nature_names() -> list[str]:
    """Lista ordenada de naturalezas para mostrar en la interfaz."""
    return sorted(NATURES.keys())


def is_neutral(nature: str) -> bool:
    """Indica si la naturaleza no modifica estadísticas."""
    boost, drop = NATURES.get(nature, (None, None))
    return boost == drop
