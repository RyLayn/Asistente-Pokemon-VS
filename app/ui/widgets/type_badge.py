"""Colores e insignias (badges) de tipo, para dar color a la interfaz."""

from __future__ import annotations

# Colores por tipo (en español), inspirados en la paleta habitual de la saga.
TYPE_COLORS: dict[str, str] = {
    "Normal": "#9099a1", "Fuego": "#ff6b3d", "Agua": "#4d90d5", "Eléctrico": "#f3d23b",
    "Planta": "#63bb5b", "Hielo": "#74cec0", "Lucha": "#ce4069", "Veneno": "#ab6ac8",
    "Tierra": "#d97746", "Volador": "#8fa9de", "Psíquico": "#f97176", "Bicho": "#90c12c",
    "Roca": "#c7b78b", "Fantasma": "#5269ac", "Dragón": "#0a6dc4", "Siniestro": "#5a5366",
    "Acero": "#5a8ea1", "Hada": "#ec8fe6",
}

_TEXT_DARK = {"Eléctrico", "Hielo", "Roca", "Hada", "Bicho"}


def type_color(t: str) -> str:
    return TYPE_COLORS.get(t, "#9099a1")


def pills_html(types: list[str], font_size: int = 11) -> str:
    """Devuelve HTML con insignias de color para una lista de tipos."""
    out = []
    for t in types:
        if not t:
            continue
        bg = type_color(t)
        fg = "#1a1a1a" if t in _TEXT_DARK else "#ffffff"
        out.append(
            f'<span style="background-color:{bg};color:{fg};'
            f'font-size:{font_size}px;font-weight:600;">&nbsp;{t}&nbsp;</span>'
        )
    return "&nbsp;".join(out)
