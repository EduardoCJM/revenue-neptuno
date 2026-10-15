from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.analysis.series import HABITACIONES_TOTALES
from src.ui.tema import (
    AMBAR,
    AZUL_OCEANO,
    COLOR_BIEN,
    COLOR_CY,
    COLOR_LY,
    COLOR_MAL,
    DORADO_ARENA,
    FUENTE,
    GRAFITO,
    GRIS_NEUTRO,
    GRIS_SUAVE,
    TERRACOTA,
    UMBRALES_LIBRES,
    VERDE_BOTANICO,
    VERDE_CLARO,
)

COLOR_POR_VENTANA = {
    "Pickup día":       TERRACOTA,
    "Pickup semana":    AZUL_OCEANO,
    "Pickup 2 semanas": VERDE_BOTANICO,
}


def _bandas_finde(df: pd.DataFrame) -> list[tuple[int, int]]:
    """Devuelve (idx_inicio, idx_fin) para cada bloque contiguo de findes (Vie-Sáb-Dom)."""
    rangos = []
    inicio = None
    for i, es_finde in enumerate(df["Es finde"].tolist()):
        if es_finde and inicio is None:
            inicio = i
        elif not es_finde and inicio is not None:
            rangos.append((inicio, i - 1))
            inicio = None
    if inicio is not None:
        rangos.append((inicio, len(df) - 1))
    return rangos


def _hex_a_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def _titulo_con_asterisco(titulo: str, df: pd.DataFrame) -> str:
    """Añade la leyenda del asterisco solo si el periodo tiene días marcados."""
    if "Bloqueadas" not in df.columns or not (df["Bloqueadas"] > 0).any():
        return titulo
    return (
        f"{titulo}<br>"
        f"<span style='font-size:12px;color:{DORADO_ARENA}'>"
        f"* día con habitaciones fuera de venta</span>"
    )


# ─────────── Libres CY vs LY (anual) ───────────
def grafico_libres_cy_vs_ly(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=df["Fecha"], y=df["Libres LY"], name="Libres LY", mode="lines",
                   line=dict(color=COLOR_LY, width=1.5),
                   fill="tozeroy", fillcolor=_hex_a_rgba(COLOR_LY, 0.18))
    )
    fig.add_trace(
        go.Scatter(x=df["Fecha"], y=df["Libres CY"], name="Libres CY", mode="lines",
                   line=dict(color=COLOR_CY, width=2.5),
                   fill="tozeroy", fillcolor=_hex_a_rgba(COLOR_CY, 0.30))
    )
    fig.update_layout(
        title=f"Habitaciones libres — CY vs LY (sobre {HABITACIONES_TOTALES})",
        xaxis_title="Fecha", yaxis_title="Libres",
        yaxis=dict(range=[0, HABITACIONES_TOTALES + 0.5]),
        hovermode="x unified",
        legend=dict(orientation="h", y=1.1),
    )
    return fig


# ─────────── Libres próximo mes (LÍNEA con marcadores grandes) ───────────
def grafico_libres_proximo_mes(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    # Bandas de fondo por umbral (color de criticidad)
    for i, (lim, etiqueta, color) in enumerate(UMBRALES_LIBRES):
        y0 = 0 if i == 0 else UMBRALES_LIBRES[i - 1][0] + 0.5
        y1 = lim + 0.5
        fig.add_hrect(y0=y0, y1=y1, fillcolor=color, opacity=0.06,
                      line_width=0, layer="below")

    # Bandas verticales para findes (Vie-Sáb-Dom)
    for ini, fin in _bandas_finde(df):
        fig.add_vrect(
            x0=ini - 0.5, x1=fin + 0.5,
            fillcolor=AZUL_OCEANO, opacity=0.07,
            line_width=0, layer="below",
        )

    fig.add_trace(
        go.Scatter(
            x=df["Etiqueta multilinea"], y=df["Libres"],
            mode="lines+markers+text",
            line=dict(color=AZUL_OCEANO, width=2.5, shape="spline", smoothing=0.6),
            marker=dict(size=14, color=df["Color"], line=dict(color="white", width=2)),
            text=df["Libres"].astype(int),
            textposition="top center",
            textfont=dict(family=FUENTE, size=12, color=GRAFITO),
            customdata=df[["Reservas", "Día semana", "Fecha", "Nota"]],
            hovertemplate=(
                "<b>%{customdata[1]} %{customdata[2]|%d/%m/%Y}</b><br>"
                "Libres: <b>%{y}</b><br>Reservas: %{customdata[0]}"
                "%{customdata[3]}<extra></extra>"
            ),
            showlegend=False,
        )
    )

    # Eje Y secundario derecho: % de ocupación equivalente a cada libre
    # 0 libres → 100%, 95 libres → 0%
    libres_ticks = list(range(0, HABITACIONES_TOTALES + 1, 10))
    pct_labels = [f"{(HABITACIONES_TOTALES - t) * 100 / HABITACIONES_TOTALES:.0f}%"
                  for t in libres_ticks]

    fig.update_layout(
        title=_titulo_con_asterisco(
            "Disponibilidad — próximos días (sombra azul = fin de semana)", df),
        xaxis_title=None,
        yaxis=dict(
            title=f"Libres (de {HABITACIONES_TOTALES})",
            range=[-0.5, HABITACIONES_TOTALES + 4],
            tickmode="array",
            tickvals=libres_ticks,
        ),
        yaxis2=dict(
            title="% Ocupación",
            range=[-0.5, HABITACIONES_TOTALES + 4],
            tickmode="array",
            tickvals=libres_ticks,
            ticktext=pct_labels,
            overlaying="y",
            side="right",
            showgrid=False,
            tickfont=dict(family=FUENTE, size=11, color=AZUL_OCEANO),
            title_font=dict(family=FUENTE, size=12, color=AZUL_OCEANO),
        ),
        xaxis=dict(
            tickangle=0,
            tickfont=dict(size=11),
            type="category",
            tickmode="array",
            tickvals=list(df["Etiqueta multilinea"]),
            ticktext=list(df["Etiqueta multilinea"]),
            automargin=True,
        ),
        margin=dict(l=60, r=70, t=70, b=80),
        height=460,
    )
    return fig


# ─────────── Libres CY vs LY filtrado a un mes ───────────
def grafico_libres_cy_vs_ly_mes(df: pd.DataFrame, mes_label: str) -> go.Figure:
    fig = go.Figure()

    # Sombras de finde
    for ini, fin in _bandas_finde(df):
        fig.add_vrect(
            x0=ini - 0.5, x1=fin + 0.5,
            fillcolor=AZUL_OCEANO, opacity=0.07,
            line_width=0, layer="below",
        )

    fig.add_trace(
        go.Scatter(
            x=df["Etiqueta multilinea"], y=df["Libres LY"],
            name="Libres LY", mode="lines+markers",
            line=dict(color=COLOR_LY, width=1.8, dash="dot"),
            marker=dict(size=8, color=COLOR_LY),
            customdata=df[["Reservas LY", "Día semana", "Fecha"]],
            hovertemplate="<b>%{customdata[1]} %{customdata[2]|%d/%m/%Y}</b><br>"
                          "Libres LY: <b>%{y:.0f}</b><br>"
                          "Reservas LY: %{customdata[0]:.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["Etiqueta multilinea"], y=df["Libres CY"],
            name="Libres CY", mode="lines+markers+text",
            line=dict(color=COLOR_CY, width=2.5),
            marker=dict(size=11, color=COLOR_CY, line=dict(color="white", width=2)),
            text=df["Libres CY"].astype(int),
            textposition="top center",
            textfont=dict(family=FUENTE, size=11, color=GRAFITO),
            customdata=df[["Reservas CY", "Día semana", "Fecha"]],
            hovertemplate="<b>%{customdata[1]} %{customdata[2]|%d/%m/%Y}</b><br>"
                          "Libres CY: <b>%{y:.0f}</b><br>"
                          "Reservas CY: %{customdata[0]:.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=f"Habitaciones libres — CY vs LY · {mes_label} (sombra azul = fin de semana)",
        xaxis_title=None, yaxis_title=f"Libres (de {HABITACIONES_TOTALES})",
        yaxis=dict(range=[-0.5, HABITACIONES_TOTALES + 1]),
        xaxis=dict(tickangle=0, tickfont=dict(size=11), type="category"),
        legend=dict(orientation="h", y=1.12),
        height=420,
        margin=dict(l=50, r=30, t=70, b=70),
    )
    return fig


# ─────────── Combinado: Libres CY/LY + Pickup diario por mes ───────────
def grafico_libres_pickup_combinado_mes(
    df_libres: pd.DataFrame,
    df_pickup: pd.DataFrame,
    ventanas: list[str],
    mes_label: str,
) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Sombras de finde (basadas en libres, que tiene la misma cuadrícula)
    for ini, fin in _bandas_finde(df_libres):
        fig.add_shape(
            type="rect",
            x0=ini - 0.5, x1=fin + 0.5,
            y0=0, y1=1, yref="y domain", xref="x",
            fillcolor=AZUL_OCEANO, opacity=0.07,
            line_width=0, layer="below",
        )

    # Pickup como barras agrupadas (eje Y derecho)
    for ventana in ventanas:
        if ventana not in COLOR_POR_VENTANA:
            continue
        color = COLOR_POR_VENTANA[ventana]
        fig.add_trace(
            go.Bar(
                x=df_pickup["Etiqueta multilinea"], y=df_pickup[ventana],
                name=ventana,
                marker=dict(color=color, line=dict(width=0), opacity=0.85),
                customdata=df_pickup[["Día semana", "Fecha"]],
                hovertemplate="<b>%{customdata[0]} %{customdata[1]|%d/%m/%Y}</b><br>"
                              + f"{ventana}: " + "<b>%{y:+.0f}</b><extra></extra>",
            ),
            secondary_y=True,
        )

    # Libres LY (eje Y izquierdo, línea punteada gris)
    fig.add_trace(
        go.Scatter(
            x=df_libres["Etiqueta multilinea"], y=df_libres["Libres LY"],
            name="Libres LY", mode="lines+markers",
            line=dict(color=COLOR_LY, width=1.8, dash="dot"),
            marker=dict(size=7, color=COLOR_LY),
            customdata=df_libres[["Reservas LY", "Día semana", "Fecha"]],
            hovertemplate="<b>%{customdata[1]} %{customdata[2]|%d/%m/%Y}</b><br>"
                          "Libres LY: <b>%{y:.0f}</b><br>"
                          "Reservas LY: %{customdata[0]:.0f}<extra></extra>",
        ),
        secondary_y=False,
    )

    # Libres CY (eje Y izquierdo, línea verde con etiquetas encima)
    fig.add_trace(
        go.Scatter(
            x=df_libres["Etiqueta multilinea"], y=df_libres["Libres CY"],
            name="Libres CY", mode="lines+markers+text",
            line=dict(color=COLOR_CY, width=2.8),
            marker=dict(size=11, color=COLOR_CY, line=dict(color="white", width=2)),
            text=df_libres["Libres CY"].astype(int),
            textposition="top center",
            textfont=dict(family=FUENTE, size=11, color=GRAFITO),
            customdata=df_libres[["Reservas CY", "Día semana", "Fecha", "Nota"]],
            hovertemplate="<b>%{customdata[1]} %{customdata[2]|%d/%m/%Y}</b><br>"
                          "Libres CY: <b>%{y:.0f}</b><br>"
                          "Reservas CY: %{customdata[0]:.0f}"
                          "%{customdata[3]}<extra></extra>",
        ),
        secondary_y=False,
    )

    fig.add_hline(y=0, line_color=GRIS_NEUTRO, line_width=1, secondary_y=True)
    fig.update_layout(
        title=_titulo_con_asterisco(
            f"Libres CY vs LY  +  Pickup diario · {mes_label} (sombra azul = fin de semana)",
            df_libres),
        barmode="group", bargap=0.15, bargroupgap=0.05,
        legend=dict(orientation="h", y=1.12),
        margin=dict(l=50, r=50, t=80, b=70),
        height=520,
    )
    fig.update_xaxes(tickangle=0, tickfont=dict(size=11), type="category")
    fig.update_yaxes(
        title_text=f"Libres (de {HABITACIONES_TOTALES})",
        range=[-0.5, HABITACIONES_TOTALES + 4],
        tickmode="linear", tick0=0, dtick=10,
        secondary_y=False,
    )

    # Eje derecho (pickup): rango fijo -20 a 50, ticks cada 5.
    fig.update_yaxes(
        title_text="Pickup (habitaciones)",
        range=[-20, 50],
        tickmode="linear", tick0=0, dtick=5,
        showgrid=False, zeroline=True, zerolinecolor=GRIS_NEUTRO,
        secondary_y=True,
    )
    return fig


# ─────────── Reservas mensuales CY vs LY ───────────
def grafico_reservas_mensuales(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["Etiqueta"], y=df["Reservas LY"],
                         name="LY", marker_color=COLOR_LY,
                         marker_line_width=0))
    fig.add_trace(go.Bar(x=df["Etiqueta"], y=df["Reservas CY"],
                         name="CY", marker_color=COLOR_CY,
                         marker_line_width=0))
    fig.update_layout(
        title="Reservas por mes — CY vs LY",
        xaxis_title="Mes", yaxis_title="Noches reservadas",
        barmode="group", legend=dict(orientation="h", y=1.1),
        bargap=0.2, bargroupgap=0.1,
    )
    return fig


# ─────────── Pickup diario por mes (3 series toggleables) ───────────
def grafico_pickup_diario_mes(df: pd.DataFrame, ventanas: list[str], mes_label: str) -> go.Figure:
    fig = go.Figure()

    # Sombras de fin de semana
    for ini, fin in _bandas_finde(df):
        fig.add_vrect(
            x0=ini - 0.5, x1=fin + 0.5,
            fillcolor=AZUL_OCEANO, opacity=0.07,
            line_width=0, layer="below",
        )

    for ventana in ventanas:
        if ventana not in COLOR_POR_VENTANA:
            continue
        color = COLOR_POR_VENTANA[ventana]
        fig.add_trace(
            go.Bar(
                x=df["Etiqueta multilinea"], y=df[ventana],
                name=ventana,
                marker=dict(color=color, line=dict(width=0)),
                customdata=df[["Día semana", "Fecha"]],
                hovertemplate="<b>%{customdata[0]} %{customdata[1]|%d/%m/%Y}</b><br>"
                              + f"{ventana}: " + "<b>%{y:+.0f}</b><extra></extra>",
            )
        )

    fig.add_hline(y=0, line_color=GRAFITO, line_width=1)
    fig.update_layout(
        title=f"Pickup diario — {mes_label} (sombra azul = fin de semana)",
        xaxis_title=None, yaxis_title="Habitaciones",
        barmode="group", bargap=0.15, bargroupgap=0.05,
        legend=dict(orientation="h", y=1.12),
        margin=dict(l=50, r=30, t=70, b=70),
        height=420,
    )
    fig.update_xaxes(tickangle=0, tickfont=dict(size=11), type="category")
    return fig


# ─────────── Pickup por ventana (3 series suavizadas) ───────────
def grafico_pickup_por_ventana(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=df["Fecha"], y=df["Pickup 2 semanas"], name="Pickup 2 semanas",
                   mode="lines", line=dict(color=VERDE_BOTANICO, width=1.5, shape="spline"),
                   fill="tozeroy", fillcolor=_hex_a_rgba(VERDE_BOTANICO, 0.20))
    )
    fig.add_trace(
        go.Scatter(x=df["Fecha"], y=df["Pickup semana"], name="Pickup semana",
                   mode="lines", line=dict(color=AZUL_OCEANO, width=1.5, shape="spline"),
                   fill="tozeroy", fillcolor=_hex_a_rgba(AZUL_OCEANO, 0.25))
    )
    fig.add_trace(
        go.Scatter(x=df["Fecha"], y=df["Pickup día"], name="Pickup día",
                   mode="lines", line=dict(color=DORADO_ARENA, width=2.5, shape="spline"),
                   fill="tozeroy", fillcolor=_hex_a_rgba(DORADO_ARENA, 0.30))
    )
    fig.update_layout(
        title="Pickup por ventana (día / semana / 2 semanas)",
        xaxis_title="Fecha", yaxis_title="Habitaciones",
        hovermode="x unified", legend=dict(orientation="h", y=1.1),
    )
    return fig


# ─────────── Pickup mensual ───────────
def grafico_pickup_mensual(df: pd.DataFrame, ventana: str) -> go.Figure:
    colores = [COLOR_BIEN if v >= 0 else COLOR_MAL for v in df["Pickup neto"]]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(x=df["Etiqueta"], y=df["Pickup neto"],
               marker_color=colores, marker_line_width=0,
               text=[f"{v:+.0f}" for v in df["Pickup neto"]],
               textposition="outside",
               textfont=dict(family=FUENTE, size=12, color=GRAFITO),
               showlegend=False)
    )
    fig.add_hline(y=0, line_color=GRAFITO, line_width=1)
    fig.update_layout(
        title=f"Pickup neto por mes — ventana «{ventana}»",
        xaxis_title="Mes", yaxis_title="Habitaciones netas",
    )
    return fig


# ─────────── ADR diario ───────────
def grafico_adr_diario(df: pd.DataFrame) -> go.Figure:
    sin_reservas = df["Reservas"] == 0
    cy_visible = df["ADR aloj. CY"].where(~sin_reservas)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=df["Fecha"], y=df["ADR aloj. LY"], name="ADR aloj. LY",
                   mode="lines", line=dict(color=COLOR_LY, width=1.5, dash="dot"),
                   hovertemplate="LY: %{y:.2f} €<extra></extra>")
    )
    fig.add_trace(
        go.Scatter(x=df["Fecha"], y=cy_visible, name="ADR aloj. CY",
                   mode="lines+markers", line=dict(color=COLOR_CY, width=2.5),
                   marker=dict(size=6, color=COLOR_CY),
                   customdata=df[["Día semana", "Reservas"]],
                   hovertemplate=(
                       "<b>%{customdata[0]} %{x|%d/%m/%Y}</b><br>"
                       "ADR CY: <b>%{y:.2f} €</b><br>"
                       "Reservas: %{customdata[1]:.0f}<extra></extra>"
                   ))
    )
    media_cy = float(cy_visible.dropna().mean()) if cy_visible.notna().any() else 0
    if media_cy:
        fig.add_hline(y=media_cy, line_dash="dash", line_color=AMBAR, opacity=0.7,
                      annotation_text=f"Media CY {media_cy:.0f} €",
                      annotation_position="right",
                      annotation_font=dict(family=FUENTE, color=AMBAR, size=11))
    fig.update_layout(
        title="ADR alojamiento — diario (¿hay margen para bajar precio?)",
        xaxis_title="Fecha de estancia", yaxis_title="€ / habitación",
        hovermode="x unified", legend=dict(orientation="h", y=1.1),
        height=380,
    )
    return fig


# ─────────── Producción mensual CY vs LY ───────────
def grafico_produccion_mensual_cy_vs_ly(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(x=df["Etiqueta"], y=df["Producción LY"], name="LY",
               marker_color=COLOR_LY, marker_line_width=0,
               text=[f"{v:,.0f} €" for v in df["Producción LY"]],
               textposition="outside",
               textfont=dict(family=FUENTE, size=10, color=GRIS_NEUTRO))
    )
    fig.add_trace(
        go.Bar(x=df["Etiqueta"], y=df["Producción CY"], name="CY",
               marker_color=COLOR_CY, marker_line_width=0,
               text=[f"{v:,.0f} €" for v in df["Producción CY"]],
               textposition="outside",
               textfont=dict(family=FUENTE, size=11, color=GRAFITO))
    )
    fig.update_layout(
        title="Producción mensual de habitación — CY vs LY (sólo alojamiento)",
        xaxis_title="Mes", yaxis_title="€",
        barmode="group", legend=dict(orientation="h", y=1.1),
        bargap=0.2, bargroupgap=0.1,
    )
    return fig


grafico_resumen_mensual = grafico_produccion_mensual_cy_vs_ly
