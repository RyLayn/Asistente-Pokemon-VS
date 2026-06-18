"""Descarga y caché local de sprites de Pokémon.

Una vez que un sprite se ha descargado, la aplicación lo sirve siempre desde
disco y nunca vuelve a depender de Internet. Si no hay conexión y el sprite no
existe, se devuelve ``None`` y la interfaz muestra un marcador de posición.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.config import SPRITE_BASE_URL
from app.models.pokemon import Pokemon
from app.utils.logger import get_logger
from app.utils.paths import images_dir, seed_images_dir

logger = get_logger(__name__)

try:
    import requests

    _HAS_REQUESTS = True
except ImportError:  # pragma: no cover
    _HAS_REQUESTS = False


class SpriteService:
    """Gestiona la obtención de sprites con caché en disco."""

    def __init__(self, enable_download: bool = True) -> None:
        self.enable_download = enable_download
        self._dir = images_dir()
        self._seed_dir = seed_images_dir()

    def _key(self, pokemon: Pokemon) -> str:
        return pokemon.sprite_key or str(pokemon.dex_number)

    def local_path(self, pokemon: Pokemon) -> Path:
        """Ruta local esperada del sprite (exista o no)."""
        return self._dir / f"{self._key(pokemon)}.png"

    def resolve_existing(self, pokemon: Pokemon) -> Optional[Path]:
        """Devuelve un sprite ya disponible (caché o semilla), sin descargar."""
        cached = self.local_path(pokemon)
        if cached.exists():
            return cached
        seeded = self._seed_dir / f"{self._key(pokemon)}.png"
        if seeded.exists():
            return seeded
        return None

    def has_sprite(self, pokemon: Pokemon) -> bool:
        return self.resolve_existing(pokemon) is not None

    def get_sprite(self, pokemon: Pokemon) -> Optional[Path]:
        """Devuelve la ruta del sprite, descargándolo si hace falta y se puede.

        Returns:
            Ruta local del sprite o ``None`` si no está disponible offline.
        """
        existing = self.resolve_existing(pokemon)
        if existing is not None:
            return existing
        if not (self.enable_download and _HAS_REQUESTS):
            return None
        return self._download(pokemon)

    def _download(self, pokemon: Pokemon) -> Optional[Path]:
        key = pokemon.sprite_key or str(pokemon.dex_number)
        url = f"{SPRITE_BASE_URL}/{key}.png"
        path = self.local_path(pokemon)
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200 and resp.content:
                path.write_bytes(resp.content)
                logger.info("Sprite descargado: %s", path.name)
                return path
            logger.warning("Sprite no encontrado (%s): %s", resp.status_code, url)
        except requests.RequestException as exc:
            logger.warning("Fallo de descarga de sprite %s: %s", url, exc)
        return None

    def prefetch(self, pokemons: list[Pokemon]) -> int:
        """Descarga por adelantado los sprites que falten. Devuelve cuántos."""
        downloaded = 0
        for mon in pokemons:
            if not self.has_sprite(mon) and self.get_sprite(mon) is not None:
                downloaded += 1
        return downloaded
