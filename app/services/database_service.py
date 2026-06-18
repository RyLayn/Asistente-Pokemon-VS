"""Servicio de base de datos local (offline) con soporte bilingüe.

Carga Pokémon, movimientos, objetos y habilidades desde JSON (semilla embebida
o dataset completo) y los mantiene en memoria. La base está en español de
España; un diccionario de equivalencias (``locale_latam.json``) permite además
reconocer y mostrar los nombres en español de Latinoamérica. La búsqueda y la
resolución reconocen SIEMPRE ambos idiomas, así que un nombre como
"Juego Rudo" (latino) o "Carantoña" (España) llevan al mismo movimiento.

Implementa el :class:`DataRepository` que consume el motor de análisis.
"""

from __future__ import annotations

import sqlite3
import unicodedata
from pathlib import Path
from typing import Optional

from app.core.repository import DataRepository
from app.import_export.team_io import _loads
from app.models.ability import Ability
from app.models.item import Item
from app.models.move import Move
from app.models.pokemon import Pokemon
from app.utils.logger import get_logger
from app.utils.paths import database_dir, database_path, seed_dir

logger = get_logger(__name__)

LANG_ES = "es"        # español de España
LANG_LATAM = "latam"  # español de Latinoamérica


def normalize(text: str) -> str:
    """Normaliza un texto para comparaciones (minúsculas, sin acentos/espacios)."""
    text = (text or "").strip().lower()
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    return text.replace(" ", "").replace("-", "").replace("'", "")


def _read_json(path: Path) -> list | dict:
    try:
        return _loads(path.read_bytes())
    except (OSError, ValueError) as exc:
        logger.warning("No se pudo leer %s: %s", path, exc)
        return []


class DatabaseService(DataRepository):
    """Acceso centralizado a los datos del juego, con idioma seleccionable."""

    def __init__(self, language: str = LANG_ES) -> None:
        self.language = language
        self._pokemon: dict[str, Pokemon] = {}
        self._moves: dict[str, Move] = {}
        self._items: dict[str, Item] = {}
        self._abilities: dict[str, Ability] = {}
        self._aliases: dict[str, dict[str, str]] = {}
        # Equivalencias España -> Latino, por categoría (nombre exacto España -> latino).
        self._latam: dict[str, dict[str, str]] = {}
        # Renombramientos de Gen 9 / Z-A (nombre antiguo normalizado -> nuevo).
        self._renamed: dict[str, dict[str, str]] = {}
        # Megaevoluciones: normalize(base) -> [{"form","stone"}, ...]
        self._mega: dict[str, list[dict]] = {}
        self.load()

    def set_language(self, language: str) -> None:
        self.language = language if language in (LANG_ES, LANG_LATAM) else LANG_ES

    # --- Carga -------------------------------------------------------------

    def _source_dir(self) -> Path:
        full = database_dir()
        if (full / "pokemon.json").exists():
            return full
        return seed_dir()

    def load(self) -> None:
        src = self._source_dir()
        logger.info("Cargando datos desde %s", src)

        for entry in _read_json(src / "pokemon.json"):
            mon = Pokemon.from_dict(entry)
            self._pokemon[normalize(mon.name)] = mon
            if mon.form:
                self._pokemon[normalize(mon.display_name)] = mon

        for entry in _read_json(src / "moves.json"):
            move = Move.from_dict(entry)
            self._moves[normalize(move.name)] = move

        for entry in _read_json(src / "items.json"):
            item = Item.from_dict(entry)
            self._items[normalize(item.name)] = item

        for entry in _read_json(src / "abilities.json"):
            ab = Ability.from_dict(entry)
            self._abilities[normalize(ab.name)] = ab

        aliases = _read_json(src / "aliases.json")
        if isinstance(aliases, dict):
            self._aliases = {
                k: {normalize(en): es for en, es in v.items()}
                for k, v in aliases.items()
            }

        self._apply_fixes(src)
        self._load_latam(src)
        self._load_mega(src)

        logger.info(
            "Datos cargados: %d Pokémon, %d movimientos, %d objetos, %d habilidades",
            len(set(id(p) for p in self._pokemon.values())),
            len(self._moves), len(self._items), len(self._abilities),
        )
        self._sync_sqlite()

    def _apply_fixes(self, src: Path) -> None:
        """Corrige nombres (renombramientos de Gen 9 / Z-A, truncamientos) y
        añade entradas que la fuente no tradujo."""
        data = _read_json(src / "fixes_es.json")
        if not isinstance(data, dict):
            return
        fix = data.get("fix", {})
        for old, new in fix.get("moves", {}).items():
            mv = self._moves.get(normalize(old))
            if mv is not None:
                mv.name = new
                self._moves[normalize(new)] = mv
            self._renamed.setdefault("moves", {})[normalize(old)] = new
        for old, new in fix.get("abilities", {}).items():
            ab = self._abilities.get(normalize(old))
            if ab is not None:
                ab.name = new
                self._abilities[normalize(new)] = ab
            self._renamed.setdefault("abilities", {})[normalize(old)] = new
        for old, new in fix.get("items", {}).items():
            it = self._items.get(normalize(old))
            if it is not None:
                it.name = new
                self._items[normalize(new)] = it
            self._renamed.setdefault("items", {})[normalize(old)] = new
        # Altas de entradas ausentes.
        add = data.get("add", {})
        for entry in add.get("moves", []):
            mv = Move.from_dict(entry)
            self._moves.setdefault(normalize(mv.name), mv)
        for entry in add.get("items", []):
            it = Item.from_dict(entry)
            self._items.setdefault(normalize(it.name), it)

    def _load_latam(self, src: Path) -> None:
        data = _read_json(src / "locale_latam.json")
        if not isinstance(data, dict):
            return
        for cat in ("moves", "abilities", "items", "pokemon"):
            mapping = data.get(cat, {})
            if not isinstance(mapping, dict):
                continue
            self._latam[cat] = {es: latam for es, latam in mapping.items()
                                if not es.startswith("_")}
        # Indexar el nombre latino como alias hacia la misma entidad.
        for es_name, latam in self._latam.get("moves", {}).items():
            mv = self._moves.get(normalize(es_name))
            if mv is not None:
                self._moves.setdefault(normalize(latam), mv)
        for es_name, latam in self._latam.get("abilities", {}).items():
            ab = self._abilities.get(normalize(es_name))
            if ab is not None:
                self._abilities.setdefault(normalize(latam), ab)
        for es_name, latam in self._latam.get("items", {}).items():
            it = self._items.get(normalize(es_name))
            if it is not None:
                self._items.setdefault(normalize(latam), it)
        for es_name, latam in self._latam.get("pokemon", {}).items():
            mon = self._pokemon.get(normalize(es_name))
            if mon is not None:
                self._pokemon.setdefault(normalize(latam), mon)

    def _load_mega(self, src: Path) -> None:
        data = _read_json(src / "mega_evolution.json")
        if isinstance(data, list):
            for e in data:
                base = e.get("base", "")
                if base:
                    self._mega.setdefault(normalize(base), []).append(e)

    def mega_options(self, species: str) -> list[dict]:
        """Megaevoluciones de una especie: lista de {"form", "stone"} (en español)."""
        out = []
        for e in self._mega.get(normalize(species), []):
            out.append({
                "form": self._localize(e["form"], "pokemon"),
                "stone": self._localize(e["stone"], "items"),
            })
        return out

    def mega_for_item(self, species: str, item: str) -> Optional[str]:
        """Si ``item`` es la Piedra Mega correcta de ``species``, devuelve la
        forma mega (nombre mostrado); si no, ``None``."""
        if not item:
            return None
        for opt in self.mega_options(species):
            if normalize(opt["stone"]) == normalize(item):
                return opt["form"]
        return None

    def has_mega(self, species: str) -> bool:
        return normalize(species) in self._mega

    def _sync_sqlite(self) -> None:
        try:
            conn = sqlite3.connect(database_path())
            cur = conn.cursor()
            cur.executescript(
                """
                CREATE TABLE IF NOT EXISTS pokemon (
                    name TEXT PRIMARY KEY, dex_number INTEGER, types TEXT, generation INTEGER
                );
                CREATE TABLE IF NOT EXISTS moves (
                    name TEXT PRIMARY KEY, type TEXT, category TEXT,
                    power INTEGER, accuracy INTEGER, pp INTEGER
                );
                """
            )
            cur.executemany(
                "INSERT OR REPLACE INTO pokemon VALUES (?,?,?,?)",
                [(p.display_name, p.dex_number, "/".join(p.types), p.generation)
                 for p in self.all_pokemon()],
            )
            cur.executemany(
                "INSERT OR REPLACE INTO moves VALUES (?,?,?,?,?,?)",
                [(m.name, m.type, m.category, m.power, m.accuracy, m.pp)
                 for m in self._unique(self._moves)],
            )
            conn.commit()
            conn.close()
        except sqlite3.Error as exc:
            logger.warning("No se pudo sincronizar SQLite: %s", exc)

    # --- Localización ------------------------------------------------------

    def _localize(self, es_name: str, cat: str) -> str:
        """Traduce un nombre al idioma activo, aplicando primero los
        renombramientos de Gen 9 / Z-A (que valen para ambos idiomas)."""
        canonical = self._renamed.get(cat, {}).get(normalize(es_name), es_name)
        if self.language == LANG_LATAM:
            return self._latam.get(cat, {}).get(canonical, canonical)
        return canonical

    def localized_pokemon(self, mon: Pokemon) -> str:
        return self._localize(mon.display_name, "pokemon")

    def localized_move(self, name_es: str) -> str:
        return self._localize(name_es, "moves")

    def localized_ability(self, name_es: str) -> str:
        return self._localize(name_es, "abilities")

    def localized_item(self, name_es: str) -> str:
        return self._localize(name_es, "items")

    # --- DataRepository ----------------------------------------------------

    def get_pokemon(self, name: str) -> Optional[Pokemon]:
        if not name:
            return None
        key = normalize(name)
        if key in self._pokemon:
            return self._pokemon[key]
        alias = self._aliases.get("pokemon", {}).get(key)
        if alias:
            return self._pokemon.get(normalize(alias))
        return None

    def get_move(self, name: str) -> Optional[Move]:
        if not name:
            return None
        key = normalize(name)
        if key in self._moves:
            return self._moves[key]
        alias = self._aliases.get("moves", {}).get(key)
        if alias:
            return self._moves.get(normalize(alias))
        return None

    def get_item(self, name: str) -> Optional[Item]:
        return self._items.get(normalize(name))

    def get_ability(self, name: str) -> Optional[Ability]:
        return self._abilities.get(normalize(name))

    # --- Resolución de nombres --------------------------------------------

    def resolve_species(self, name: str) -> str:
        mon = self.get_pokemon(name)
        return self.localized_pokemon(mon) if mon else name

    def resolve_move(self, name: str) -> str:
        move = self.get_move(name)
        return self.localized_move(move.name) if move else name

    def resolve_item(self, name: str) -> str:
        it = self.get_item(name)
        if it is not None:
            return self.localized_item(it.name)
        alias = self._aliases.get("items", {}).get(normalize(name))
        return alias or name

    def resolve_ability(self, name: str) -> str:
        ab = self.get_ability(name)
        if ab is not None:
            return self.localized_ability(ab.name)
        alias = self._aliases.get("abilities", {}).get(normalize(name))
        return alias or name

    # --- Listados para la interfaz ----------------------------------------

    def all_pokemon(self) -> list[Pokemon]:
        seen: dict[int, Pokemon] = {}
        for mon in self._pokemon.values():
            seen[id(mon)] = mon
        return sorted(seen.values(), key=lambda p: (p.dex_number, p.form))

    def _unique(self, mapping: dict) -> list:
        seen: dict[int, object] = {}
        for v in mapping.values():
            seen[id(v)] = v
        return list(seen.values())

    # Nombres en el idioma activo (para combos, etiquetas).
    def all_pokemon_names(self) -> list[str]:
        return [self.localized_pokemon(p) for p in self.all_pokemon()]

    def all_move_names(self) -> list[str]:
        return sorted(self.localized_move(m.name) for m in self._unique(self._moves))

    def all_item_names(self) -> list[str]:
        return sorted(self.localized_item(i.name) for i in self._unique(self._items))

    def all_ability_names(self) -> list[str]:
        return sorted(self.localized_ability(a.name) for a in self._unique(self._abilities))

    # Nombres en AMBOS idiomas (para que la búsqueda encuentre cualquiera).
    def _bilingual(self, names_es: list[str], cat: str) -> list[str]:
        out = set(names_es)
        for es, latam in self._latam.get(cat, {}).items():
            out.add(latam)
        return sorted(out)

    def search_pokemon_names(self) -> list[str]:
        return self._bilingual([p.display_name for p in self.all_pokemon()], "pokemon")

    def search_move_names(self) -> list[str]:
        return self._bilingual([m.name for m in self._unique(self._moves)], "moves")

    def search_item_names(self) -> list[str]:
        return self._bilingual([i.name for i in self._unique(self._items)], "items")

    def search_ability_names(self) -> list[str]:
        return self._bilingual([a.name for a in self._unique(self._abilities)], "abilities")
