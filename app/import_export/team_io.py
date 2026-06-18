"""Persistencia de equipos en disco usando JSON.

Cada equipo se guarda como ``<team_id>.json`` dentro de la carpeta de equipos.
Se usa :mod:`orjson` si está disponible (más rápido) y se recurre al ``json``
estándar como alternativa, de modo que la aplicación funcione siempre.
"""

from __future__ import annotations

from pathlib import Path

from app.models.team import Team
from app.utils.logger import get_logger
from app.utils.paths import teams_dir

logger = get_logger(__name__)

try:  # pragma: no cover - selección de backend en tiempo de import
    import orjson

    def _dumps(data: dict) -> bytes:
        return orjson.dumps(data, option=orjson.OPT_INDENT_2)

    def _loads(raw: bytes) -> dict:
        return orjson.loads(raw)

    _BINARY = True
except ImportError:  # pragma: no cover
    import json

    def _dumps(data: dict) -> bytes:
        return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

    def _loads(raw: bytes) -> dict:
        return json.loads(raw.decode("utf-8"))

    _BINARY = True


def save_team(team: Team, directory: Path | None = None) -> Path:
    """Guarda un equipo y devuelve la ruta del fichero."""
    directory = directory or teams_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{team.team_id}.json"
    path.write_bytes(_dumps(team.to_dict()))
    logger.info("Equipo guardado: %s", path)
    return path


def load_team(path: Path) -> Team:
    """Carga un equipo desde un fichero JSON."""
    data = _loads(Path(path).read_bytes())
    return Team.from_dict(data)


def load_all_teams(directory: Path | None = None) -> list[Team]:
    """Carga todos los equipos guardados de la carpeta de equipos."""
    directory = directory or teams_dir()
    teams: list[Team] = []
    if not directory.exists():
        return teams
    for path in sorted(directory.glob("*.json")):
        try:
            teams.append(load_team(path))
        except (ValueError, OSError) as exc:
            logger.warning("No se pudo cargar %s: %s", path, exc)
    return teams


def delete_team(team_id: str, directory: Path | None = None) -> bool:
    """Elimina el fichero de un equipo. Devuelve True si existía."""
    directory = directory or teams_dir()
    path = directory / f"{team_id}.json"
    if path.exists():
        path.unlink()
        logger.info("Equipo eliminado: %s", path)
        return True
    return False
