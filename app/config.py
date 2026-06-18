"""Constantes y configuración global de la aplicación.

Pokémon Champions Assistant — asistente de combate offline.
Creado por RyLayn (https://github.com/RyLayn).
© 2026 RyLayn. Conserva esta atribución en cualquier copia o modificación.
"""

from __future__ import annotations

from dataclasses import dataclass

APP_NAME = "Pokémon Champions Assistant"
APP_VERSION = "1.0.0"

# Autoría del proyecto. La interfaz muestra estos datos (menú "Acerca de" y pie
# de la ventana); forman parte del producto y deben conservarse.
APP_AUTHOR = "RyLayn"
APP_AUTHOR_URL = "https://github.com/RyLayn"
APP_COPYRIGHT = "© 2026 RyLayn"

# Generación máxima soportada por la arquitectura de datos.
# La aplicación está preparada hasta Leyendas Pokémon Z-A y Pokémon Champions.
MAX_GENERATION = 9
SUPPORTED_GAMES = ("Hasta Leyendas Pokémon Z-A", "Pokémon Champions")

TEAM_SIZE = 6
MOVES_PER_POKEMON = 4

# Modos de combate de Pokémon Champions.
MODE_SINGLES = "singles"
MODE_DOUBLES = "doubles"
MODE_LABELS = {MODE_SINGLES: "Combate Individual", MODE_DOUBLES: "Combate Dobles"}
# Pokémon que se seleccionan para la batalla (Bring 6 Pick N).
PICK_COUNT = {MODE_SINGLES: 3, MODE_DOUBLES: 4}
# Pokémon activos en el campo por bando.
ACTIVE_COUNT = {MODE_SINGLES: 1, MODE_DOUBLES: 2}

# Fuente offline para construir la base de datos local de sprites/datos.
SPRITE_BASE_URL = (
    "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon"
)
POKEAPI_BASE_URL = "https://pokeapi.co/api/v2"


@dataclass(slots=True)
class Settings:
    """Ajustes de usuario persistibles."""

    theme: str = "dark"  # "dark" | "light"
    language: str = "es"
    download_sprites: bool = True
    mode: str = MODE_SINGLES  # "singles" | "doubles"

    def to_dict(self) -> dict:
        return {
            "theme": self.theme,
            "language": self.language,
            "download_sprites": self.download_sprites,
            "mode": self.mode,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        return cls(
            theme=data.get("theme", "dark"),
            language=data.get("language", "es"),
            download_sprites=bool(data.get("download_sprites", True)),
            mode=data.get("mode", MODE_SINGLES),
        )
