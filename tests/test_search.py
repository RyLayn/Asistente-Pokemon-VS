"""Pruebas del servicio de búsqueda predictiva."""

from app.services.search_service import SearchService

NAMES = [
    "Garchomp", "Gardevoir", "Garganacl", "Gengar", "Greninja",
    "Charizard", "Dragonite", "Pikachu",
]


def test_prefix_results_come_first():
    svc = SearchService(NAMES)
    results = svc.search("gar", limit=8)
    # Los tres que empiezan por "gar" deben aparecer y primero.
    assert results[:3] == ["Garchomp", "Gardevoir", "Garganacl"]


def test_search_is_case_insensitive():
    svc = SearchService(NAMES)
    assert "Charizard" in svc.search("CHAR")


def test_best_match_exact():
    svc = SearchService(NAMES)
    assert svc.best_match("pikachu") == "Pikachu"


def test_empty_query_returns_empty():
    svc = SearchService(NAMES)
    assert svc.search("") == []
