"""Paleta y tipografía Neptuno Costa Adeje.

Inspirado en el logo (azul cobalto profundo + sol estilizado) y las
piscinas turquesa con vistas al mar del aparthotel en Costa Adeje (Tenerife).
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

# ─── Paleta Neptuno Costa Adeje ───
AZUL_COBALTO   = "#240B80"   # primario, color literal del logo
AZUL_PROFUNDO  = "#3B2199"   # variante para gradientes
TURQUESA       = "#0EA5C7"   # secundario, agua piscina
AZUL_PISCINA   = "#5BCBE0"   # tono claro turquesa
DORADO_SOL     = "#F4B860"   # acento positivo (sol canario)
CORAL          = "#E07856"   # acento cálido / atardecer
TERRACOTA      = "#C0492B"   # crítico / negativo
AMBAR          = "#E0A458"   # atención
CREMA          = "#F5EFE6"   # fondo arena
GRAFITO        = "#1F2937"   # texto
GRIS_NEUTRO    = "#9CA3AF"   # LY / referencia
GRIS_SUAVE     = "#E5E7EB"   # bordes / grids

# Semánticos (los que usan los gráficos sin saber del hotel)
COLOR_CY      = AZUL_COBALTO
COLOR_LY      = GRIS_NEUTRO
COLOR_BIEN    = TURQUESA
COLOR_MAL     = TERRACOTA
COLOR_NEUTRO  = DORADO_SOL

# Aliases para compatibilidad con graficos.py (que usa nombres antiguos)
VERDE_BOTANICO = AZUL_COBALTO    # ahora "primario CY"
VERDE_CLARO    = TURQUESA        # ahora "positivo / bien"
AZUL_OCEANO    = TURQUESA        # ahora "acento de mar / findes"
AZUL_CLARO     = AZUL_PISCINA
DORADO_ARENA   = DORADO_SOL
MARFIL         = CREMA

# Umbrales de habitaciones libres sobre 95
# (95 - libres) / 95 = % ocupación → 0 libres = 100%, 10 libres = 89%, 40 libres = 58%
UMBRALES_LIBRES = [
    (10, "Excelente",  AZUL_COBALTO),    # 0-10  libres → ≥89% ocup
    (20, "Bien",       TURQUESA),        # 11-20         → 79-88%
    (40, "Atención",   AMBAR),           # 21-40         → 58-78%
    (95, "Crítico",    TERRACOTA),       # 41-95         → ≤57%
]

FUENTE = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"


def color_por_libres(libres: float) -> str:
    for lim, _et, col in UMBRALES_LIBRES:
        if libres <= lim:
            return col
    return UMBRALES_LIBRES[-1][2]


def color_pickup(valor: float, ref_pos: float = 5.0) -> str:
    """Escala divergente: rojo si <=0, ámbar si bajo, verde si alto."""
    if valor <= 0:
        return TERRACOTA
    if valor < ref_pos / 2:
        return AMBAR
    if valor < ref_pos:
        return DORADO_SOL
    return TURQUESA


# ─── Plantilla Plotly ───
TEMPLATE = go.layout.Template()
TEMPLATE.layout = go.Layout(
    font=dict(family=FUENTE, color=GRAFITO, size=13),
    title=dict(font=dict(family=FUENTE, size=16, color=GRAFITO), x=0.0, xanchor="left"),
    paper_bgcolor="white",
    plot_bgcolor="white",
    colorway=[AZUL_COBALTO, TURQUESA, DORADO_SOL, CORAL, AMBAR, AZUL_PISCINA, TERRACOTA],
    xaxis=dict(
        showgrid=False, showline=True, linecolor=GRIS_SUAVE, linewidth=1,
        ticks="outside", tickcolor=GRIS_SUAVE, tickfont=dict(family=FUENTE, size=12),
    ),
    yaxis=dict(
        showgrid=True, gridcolor=GRIS_SUAVE, gridwidth=1,
        showline=False, ticks="", tickfont=dict(family=FUENTE, size=12),
        zerolinecolor=GRIS_SUAVE,
    ),
    legend=dict(
        bgcolor="rgba(255,255,255,0)", bordercolor="rgba(0,0,0,0)",
        font=dict(family=FUENTE, size=12),
    ),
    margin=dict(l=50, r=30, t=70, b=50),
    hoverlabel=dict(bgcolor="white", bordercolor=GRIS_SUAVE, font=dict(family=FUENTE, size=12)),
)
pio.templates["costadeje"] = TEMPLATE
pio.templates.default = "costadeje"


# ─── CSS para Streamlit ───
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp, .stMarkdown, .stMetric, .stButton, .stSelectbox, .stRadio {{
    font-family: {FUENTE};
}}

h1, h2, h3, h4 {{
    font-family: {FUENTE};
    font-weight: 700;
    color: {GRAFITO};
    letter-spacing: -0.01em;
}}

h1 {{
    border-bottom: 3px solid {AZUL_COBALTO};
    padding-bottom: 0.4rem;
    display: inline-block;
}}

[data-testid="stMetricValue"] {{
    font-family: {FUENTE};
    font-weight: 700;
    color: {GRAFITO};
    font-size: 1.6rem;
}}

[data-testid="stMetricLabel"] {{
    font-family: {FUENTE};
    font-weight: 500;
    color: #6B7280;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}

[data-testid="stMetricDelta"] {{
    font-family: {FUENTE};
    font-weight: 600;
    font-size: 0.9rem;
}}

[data-testid="stSidebar"] {{
    background-color: {CREMA};
    border-right: 1px solid {GRIS_SUAVE};
}}

.stDataFrame, .stTable {{
    font-family: {FUENTE};
}}

div[data-testid="stExpander"] {{
    border: 1px solid {GRIS_SUAVE};
    border-radius: 8px;
}}

/* Bandera de marca arriba: azul cobalto → turquesa */
.brand-bar {{
    background: linear-gradient(90deg, {AZUL_COBALTO} 0%, {TURQUESA} 100%);
    color: white;
    padding: 0.6rem 1.2rem;
    border-radius: 8px;
    margin-bottom: 1rem;
    font-family: {FUENTE};
    font-weight: 600;
    letter-spacing: 0.03em;
    box-shadow: 0 2px 8px rgba(36, 11, 128, 0.15);
}}

.brand-header {{
    display: flex;
    align-items: center;
    gap: 1.5rem;
    padding: 1rem 0 0.5rem 0;
    border-bottom: 1px solid {GRIS_SUAVE};
    margin-bottom: 1rem;
}}

.brand-header img.logo {{
    height: 64px;
    width: auto;
}}

.brand-header img.hero {{
    height: 90px;
    width: auto;
    border-radius: 8px;
    object-fit: cover;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}}

.brand-header .brand-text {{
    flex: 1;
}}

.brand-header h2 {{
    margin: 0;
    color: {AZUL_COBALTO};
    font-size: 1.5rem;
    font-weight: 700;
}}

.brand-header p.tagline {{
    margin: 0.2rem 0 0 0;
    color: {GRIS_NEUTRO};
    font-size: 0.95rem;
    font-style: italic;
}}

.legend-pill {{
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 600;
    margin-right: 0.4rem;
    color: white;
    font-family: {FUENTE};
}}
</style>
"""
