"""Importación y exportación en formato *Pokémon Showdown*.

El parser reconoce especie, apodo, objeto, habilidad, naturaleza, tera tipo,
nivel y los cuatro movimientos. Traduce las naturalezas y los tipos del inglés
(formato Showdown) al español usado internamente. La resolución de nombres de
especie/movimiento contra la base de datos en español la realiza el servicio
de datos mediante alias y búsqueda difusa.
"""

from __future__ import annotations

import re

from app.models.pokemon_set import PokemonSet

# Traducción de naturalezas inglés <-> español.
NATURE_EN_ES: dict[str, str] = {
    "Hardy": "Fuerte", "Lonely": "Huraña", "Brave": "Audaz", "Adamant": "Firme",
    "Naughty": "Pícara", "Bold": "Osada", "Docile": "Dócil", "Relaxed": "Plácida",
    "Impish": "Agitada", "Lax": "Floja", "Timid": "Miedosa", "Hasty": "Activa",
    "Serious": "Seria", "Jolly": "Alegre", "Naive": "Ingenua", "Modest": "Modesta",
    "Mild": "Afable", "Quiet": "Mansa", "Bashful": "Tímida", "Rash": "Alocada",
    "Calm": "Serena", "Gentle": "Amable", "Sassy": "Grosera", "Careful": "Cauta",
    "Quirky": "Rara",
}
NATURE_ES_EN: dict[str, str] = {v: k for k, v in NATURE_EN_ES.items()}

# Traducción de tipos inglés <-> español (para el Tera tipo).
TYPE_EN_ES: dict[str, str] = {
    "Normal": "Normal", "Fire": "Fuego", "Water": "Agua", "Electric": "Eléctrico",
    "Grass": "Planta", "Ice": "Hielo", "Fighting": "Lucha", "Poison": "Veneno",
    "Ground": "Tierra", "Flying": "Volador", "Psychic": "Psíquico", "Bug": "Bicho",
    "Rock": "Roca", "Ghost": "Fantasma", "Dragon": "Dragón", "Dark": "Siniestro",
    "Steel": "Acero", "Fairy": "Hada", "Stellar": "Astral",
}
TYPE_ES_EN: dict[str, str] = {v: k for k, v in TYPE_EN_ES.items()}

_HEADER_RE = re.compile(r"^(?P<head>.*?)(?:\s*@\s*(?P<item>.+))?$")
_PAREN_RE = re.compile(r"^(?P<a>.+?)\s*\((?P<b>[^)]+)\)\s*$")


def _parse_header(line: str) -> tuple[str, str, str]:
    """Analiza la primera línea: devuelve (especie, apodo, objeto)."""
    item = ""
    if "@" in line:
        left, item = line.split("@", 1)
        item = item.strip()
    else:
        left = line
    left = left.strip()

    nickname = ""
    species = left
    m = _PAREN_RE.match(left)
    if m:
        a, b = m.group("a").strip(), m.group("b").strip()
        # "(M)" / "(F)" son género, no especie.
        if b in ("M", "F"):
            species = a
        else:
            nickname, species = a, b
    return species, nickname, item


def parse_set(block: str) -> PokemonSet | None:
    """Convierte un bloque de texto Showdown en un :class:`PokemonSet`."""
    lines = [ln.rstrip() for ln in block.splitlines() if ln.strip()]
    if not lines:
        return None

    species, nickname, item = _parse_header(lines[0])
    if not species:
        return None

    pset = PokemonSet(species=species, nickname=nickname, item=item)
    moves: list[str] = []

    for line in lines[1:]:
        stripped = line.strip()
        low = stripped.lower()
        if low.startswith("ability:"):
            pset.ability = stripped.split(":", 1)[1].strip()
        elif low.startswith("level:"):
            try:
                pset.level = int(stripped.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif low.startswith("tera type:"):
            raw = stripped.split(":", 1)[1].strip()
            pset.tera_type = TYPE_EN_ES.get(raw, raw)
        elif low.endswith("nature"):
            raw = stripped.rsplit(" ", 1)[0].strip()
            pset.nature = NATURE_EN_ES.get(raw, raw)
        elif stripped.startswith("-") or stripped.startswith("~"):
            move = stripped[1:].strip()
            # Algunos movimientos llevan "[tipo]" tras barra; tomar el principal.
            move = move.split("/")[0].strip()
            if move:
                moves.append(move)
        # Las líneas EVs/IVs no afectan al análisis de tipos y se ignoran.

    pset.moves = moves
    pset.__post_init__()  # normaliza a 4 ranuras
    return pset


def parse_team(text: str) -> list[PokemonSet]:
    """Convierte un export completo de Showdown en una lista de sets."""
    # Los Pokémon se separan por una o más líneas en blanco.
    blocks = re.split(r"\n\s*\n", text.strip())
    result: list[PokemonSet] = []
    for block in blocks:
        if not block.strip():
            continue
        pset = parse_set(block)
        if pset is not None:
            result.append(pset)
    return result


def export_set(pset: PokemonSet) -> str:
    """Exporta un :class:`PokemonSet` al formato Showdown."""
    head = pset.species
    if pset.nickname:
        head = f"{pset.nickname} ({pset.species})"
    if pset.item:
        head += f" @ {pset.item}"

    lines = [head]
    if pset.ability:
        lines.append(f"Ability: {pset.ability}")
    if pset.level and pset.level != 100:
        lines.append(f"Level: {pset.level}")
    if pset.tera_type:
        tera = TYPE_ES_EN.get(pset.tera_type, pset.tera_type)
        lines.append(f"Tera Type: {tera}")
    if pset.nature:
        nature = NATURE_ES_EN.get(pset.nature, pset.nature)
        lines.append(f"{nature} Nature")
    for move in pset.moves:
        if move:
            lines.append(f"- {move}")
    return "\n".join(lines)


def export_team(members: list[PokemonSet]) -> str:
    """Exporta varios sets al formato Showdown separados por línea en blanco."""
    blocks = [export_set(m) for m in members if not m.is_empty]
    return "\n\n".join(blocks)
