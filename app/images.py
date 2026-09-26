"""Genererte SVG-plasshaldarar: produktfarge + ikon for kategori. Ingen eksterne bilder."""

ICONS = {
    "jakker": (
        '<path d="M150 82 L182 68 Q200 86 218 68 L250 82 L292 132 L264 154 L250 136 V236 H150 V136 L136 154 L108 132 Z"/>'
        '<path d="M200 86 V236" stroke="{bg}" stroke-width="5" fill="none"/>'
        '<rect x="160" y="170" width="24" height="5" rx="2" fill="{bg}"/><rect x="216" y="170" width="24" height="5" rx="2" fill="{bg}"/>'
    ),
    "sko": (
        '<path d="M135 78 H190 V146 C190 162 202 169 220 175 L274 192 C290 197 298 208 298 222 V238 H135 Z"/>'
        '<path d="M124 238 H304 V254 H124 Z" opacity=".7"/>'
        '<path d="M150 100 H180 M150 116 H180 M150 132 H180" stroke="{bg}" stroke-width="5" fill="none" stroke-linecap="round"/>'
    ),
    "sekker": (
        '<rect x="148" y="74" width="104" height="160" rx="38"/>'
        '<path d="M178 74 V60 Q200 50 222 60 V74" stroke="#fff" stroke-width="7" fill="none" opacity=".9"/>'
        '<rect x="164" y="158" width="72" height="58" rx="14" fill="{bg}" opacity=".55"/>'
        '<path d="M148 110 Q126 150 148 200 M252 110 Q274 150 252 200" stroke="#fff" stroke-width="8" fill="none" opacity=".8"/>'
    ),
    "telt-sovepose": (
        '<path d="M200 66 L316 236 H84 Z"/>'
        '<path d="M200 132 L242 236 H158 Z" fill="{bg}" opacity=".6"/>'
        '<path d="M60 240 H340" stroke="#fff" stroke-width="6" stroke-linecap="round" opacity=".8"/>'
    ),
    "tilbehor": (
        '<circle cx="200" cy="150" r="78" fill="none" stroke="#fff" stroke-width="12"/>'
        '<path d="M200 90 L222 150 L200 210 L178 150 Z"/>'
        '<circle cx="200" cy="150" r="9" fill="{bg}"/>'
    ),
}


def _shade(hex_color: str, factor: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, int(c * factor))) for c in (r, g, b)))


def placeholder_svg(color: str, category: str) -> str:
    dark = _shade(color, 0.72)
    light = _shade(color, 1.12)
    icon = ICONS.get(category, ICONS["tilbehor"]).format(bg=dark)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" role="img" aria-label="Produktbilde (plasshaldar)">'
        f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{light}"/>'
        f'<stop offset="1" stop-color="{dark}"/></linearGradient></defs>'
        '<rect width="400" height="300" fill="url(#g)"/>'
        f'<g fill="#fff" fill-opacity=".92">{icon}</g></svg>'
    )
