"""Búsqueda rápida y predictiva sobre listas de nombres.

Usa RapidFuzz si está disponible para tolerar erratas y coincidencias
parciales; si no, recurre a una búsqueda por subcadena para garantizar que la
aplicación funcione sin la dependencia.
"""

from __future__ import annotations

import unicodedata

try:
    from rapidfuzz import fuzz, process

    _HAS_RAPIDFUZZ = True
except ImportError:  # pragma: no cover
    _HAS_RAPIDFUZZ = False


def _norm(text: str) -> str:
    text = text.strip().lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


class SearchService:
    """Indexa una colección de nombres y permite búsquedas predictivas."""

    def __init__(self, names: list[str] | None = None) -> None:
        self._names: list[str] = []
        self._norm_to_name: dict[str, str] = {}
        if names:
            self.set_names(names)

    def set_names(self, names: list[str]) -> None:
        """Reemplaza el índice de nombres."""
        self._names = list(names)
        self._norm_to_name = {_norm(n): n for n in names}

    def search(self, query: str, limit: int = 8) -> list[str]:
        """Devuelve hasta ``limit`` coincidencias ordenadas por relevancia.

        Prioriza los nombres que *empiezan* por la consulta (búsqueda
        predictiva tipo autocompletado) y completa con coincidencias difusas.
        """
        query = query.strip()
        if not query:
            return []

        nq = _norm(query)

        # 1) Prefijo (lo más relevante para autocompletar).
        prefix = [n for n in self._names if _norm(n).startswith(nq)]
        prefix.sort(key=str.lower)

        if len(prefix) >= limit:
            return prefix[:limit]

        # 2) Subcadena.
        contains = [
            n for n in self._names
            if nq in _norm(n) and n not in prefix
        ]
        contains.sort(key=str.lower)

        results = prefix + contains
        if len(results) >= limit or not _HAS_RAPIDFUZZ:
            return results[:limit]

        # 3) Difusa (RapidFuzz) para erratas.
        already = set(results)
        candidates = [n for n in self._names if n not in already]
        fuzzy = process.extract(
            query, candidates, scorer=fuzz.WRatio, limit=limit - len(results)
        )
        results.extend(name for name, score, _ in fuzzy if score >= 60)
        return results[:limit]

    def best_match(self, query: str) -> str | None:
        """Mejor coincidencia única (útil para resolver importaciones)."""
        matches = self.search(query, limit=1)
        return matches[0] if matches else None
