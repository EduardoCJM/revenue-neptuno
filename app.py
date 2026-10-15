from __future__ import annotations

import base64
from pathlib import Path

import pandas as pd
import streamlit as st

from src.ingest.excel_reader import FormatoExcelInvalido
from src.ingest.pipeline import avisos_inventario, procesar_excel
from src.storage.almacen import ErrorAlmacen, crear_almacen, historico_a_bytes

# El tema debe importarse antes que los gráficos para registrar el template Plotly
from src.ui.tema import (
    AZUL_COBALTO,
    COLOR_BIEN,
    COLOR_MAL,
    CSS,
    GRAFITO,
    GRIS_NEUTRO,
    UMBRALES_LIBRES,
)
from src.analysis.series import (
    HABITACIONES_TOTALES,
    adr_diario,
    dias_bloqueados,
    kpis_globales,
    libres_cy_vs_ly,
    libres_cy_vs_ly_mes,
    libres_proximo_mes,
    etiqueta_mes,
    meses_disponibles,
    pickup_diario_mes,
    pickup_mensual,
    pickup_por_ventana,
    produccion_mensual_cy_vs_ly,
    reservas_mensuales_cy_vs_ly,
    tabla_mensual_completa,
)
from src.ui.graficos import (
    grafico_adr_diario,
    grafico_libres_cy_vs_ly,
    grafico_libres_pickup_combinado_mes,
    grafico_libres_proximo_mes,
    grafico_pickup_diario_mes,
    grafico_pickup_mensual,
    grafico_pickup_por_ventana,
    grafico_produccion_mensual_cy_vs_ly,
    grafico_reservas_mensuales,
)

RAIZ = Path(__file__).resolve().parent
LOGO = RAIZ / "assets" / "logo.png"
HERO = RAIZ / "assets" / "hero_piscina.jpg"

st.set_page_config(
    page_title="Neptuno Costa Adeje · Revenue",
    page_icon=str(LOGO) if LOGO.exists() else "🌊",
    layout="wide",
)
st.markdown(CSS, unsafe_allow_html=True)


def _img_base64(ruta: Path) -> str:
    if not ruta.exists():
        return ""
    return base64.b64encode(ruta.read_bytes()).decode()


@st.cache_data(show_spinner="Leyendo histórico...")
def cargar_historico(version: str) -> pd.DataFrame | None:
    """El histórico del almacén activo.

    `version` no se usa dentro: es la clave de caché. Cambia cuando cambia el
    histórico (fecha de modificación en local, sha del fichero en GitHub), y
    así Streamlit sabe que tiene que releer.
    """
    return crear_almacen(RAIZ).leer_historico()


@st.cache_data(show_spinner=False)
def historico_descargable(version: str, df: pd.DataFrame) -> bytes:
    """El histórico como .xlsx para el botón de descarga.

    Se genera desde el DataFrame ya en memoria y se cachea: convertir 2.500+
    filas por 151 columnas tarda lo suyo, y si no, se rehace en cada clic.
    """
    return historico_a_bytes(df)


# Umbral a partir del cual se avisa de que el token esta por caducar.
# Un mes da margen de sobra para renovarlo sin prisas, y como el dashboard se
# mira una vez por semana, garantiza al menos 4 avisos antes del corte.
DIAS_AVISO_TOKEN = 30


def _aviso_caducidad(almacen) -> None:
    """Avisa de que la credencial de GitHub esta a punto de caducar.

    Cuando caduca, la app deja de poder guardar: es mejor enterarse con un mes
    de margen que un lunes con el Excel en la mano.
    """
    dias = almacen.dias_hasta_caducidad()
    if dias is None or dias > DIAS_AVISO_TOKEN:
        return

    pasos = (
        "**Cómo renovarlo:** entra en "
        "[tus tokens de GitHub](https://github.com/settings/personal-access-tokens), "
        "abre el del hotel, pulsa **Regenerate token**, copia el nuevo y pégalo en "
        "*Settings → Secrets* de esta app. Dos minutos."
    )
    if dias <= 0:
        st.error("🔴 **La credencial de GitHub ha caducado.** La app ya no puede "
                 "guardar cargas nuevas.\n\n" + pasos)
    elif dias <= 7:
        st.error(f"🔴 **La credencial de GitHub caduca en {dias} día(s).** Cuando "
                 f"caduque no podrás cargar el Excel del lunes.\n\n" + pasos)
    else:
        st.warning(f"🟠 **La credencial de GitHub caduca en {dias} días.** "
                   f"Conviene renovarla antes de que te pille.\n\n" + pasos)


def _seccion_carga(almacen) -> None:
    """Subida del Excel semanal desde el navegador."""
    with st.expander("📥 Cargar el Excel del lunes", expanded=False):
        subido = st.file_uploader(
            "Arrastra aquí el `Planning de PickUpADR`",
            type=["xlsx"],
            help="Se valida, se añade al histórico y se archiva por mes y semana.",
        )
        if subido is None:
            return

        if not st.button("Cargar al histórico", type="primary"):
            return

        try:
            with st.spinner("Validando y guardando..."):
                res = procesar_excel(subido.getvalue(), subido.name, almacen)
        except FormatoExcelInvalido as e:
            st.error(f"**Excel rechazado.** {e}")
            return
        except ErrorAlmacen as e:
            st.error(f"**No se pudo guardar.** {e}")
            return

        fecha = res["snapshot"]
        st.success(
            f"**{res['nombre']}** cargado · snapshot "
            f"{pd.Timestamp(fecha).strftime('%d/%m/%Y')} · "
            f"{res['filas_totales']:,} filas en {res['snapshots']} snapshot(s)."
        )
        for aviso in avisos_inventario(res["inventario"]):
            st.warning(aviso)
        st.caption(f"Original archivado en `{res['destino']}`.")

        # El histórico ha cambiado: hay que releerlo.
        cargar_historico.clear()
        st.rerun()


def _delta_pct(cy: float, ly: float) -> str | None:
    if not ly:
        return None
    return f"{(cy - ly) / ly * 100:+.1f} %"


def _estilo_tabla(df: pd.DataFrame):
    """Tabla mensual con resaltado visual:
    - Fila completa de meses críticos (Δ Producción <= -15%) en fondo rojo claro.
    - Producción CY (Alojamiento) en negrita y fondo azul claro.
    - Δ % en escala bicolor: verde si positivo, rojo si negativo (intensidad por valor).
    - Δ Producción €: barra de fondo (data bars) para ver magnitud de un vistazo.
    """
    cols_pct = ["Δ Producción (%)", "Δ ADR (%)", "Δ Ocup (pp)"]

    def color_pct(v):
        if pd.isna(v):
            return ""
        if v >= 5:
            return "color: #FFFFFF; background-color: #16A34A; font-weight: 700;"
        if v > 0:
            return f"color: {COLOR_BIEN}; font-weight: 700;"
        if v <= -15:
            return "color: #FFFFFF; background-color: #B91C1C; font-weight: 800;"
        if v < 0:
            return f"color: {COLOR_MAL}; font-weight: 700;"
        return f"color: {GRIS_NEUTRO};"

    def color_delta_eur(v):
        if pd.isna(v):
            return ""
        if v > 0:
            return f"color: {COLOR_BIEN}; font-weight: 700;"
        if v < 0:
            return f"color: {COLOR_MAL}; font-weight: 700;"
        return f"color: {GRIS_NEUTRO};"

    def fila_mes_critico(row):
        crit = pd.notna(row["Δ Producción (%)"]) and row["Δ Producción (%)"] <= -15
        return ["background-color: #FEF2F2;" if crit else "" for _ in row]

    return (
        df.style
        .apply(fila_mes_critico, axis=1)
        .map(color_pct, subset=cols_pct)
        .map(color_delta_eur, subset=["Δ Producción (€)", "Δ ADR (€)"])
        .bar(subset=["Producción CY (€)"], color="#DBEAFE", align="left", width=85)
        .set_properties(subset=["Producción CY (€)"],
                        **{"font-weight": "800", "color": GRAFITO})
        .set_properties(subset=["Mes"],
                        **{"font-weight": "700", "color": AZUL_COBALTO,
                           "border-left": f"4px solid {AZUL_COBALTO}",
                           "padding-left": "12px"})
        .format({
            "Producción CY (€)": "{:,.0f} €",
            "Producción LY (€)": "{:,.0f} €",
            "Δ Producción (€)": "{:+,.0f} €",
            "Δ Producción (%)": "{:+.1f} %",
            "ADR CY (€)": "{:,.2f} €",
            "ADR LY (€)": "{:,.2f} €",
            "Δ ADR (€)": "{:+,.2f} €",
            "Δ ADR (%)": "{:+.1f} %",
            "Ocup CY (%)": "{:.1f} %",
            "Ocup LY (%)": "{:.1f} %",
            "Δ Ocup (pp)": "{:+.1f} pp",
        }, na_rep="—")
        .set_table_styles([
            {"selector": "thead th",
             "props": [("background-color", AZUL_COBALTO), ("color", "white"),
                       ("font-weight", "700"), ("text-align", "center"),
                       ("padding", "10px 8px"), ("font-size", "0.85rem"),
                       ("text-transform", "uppercase"),
                       ("letter-spacing", "0.04em"),
                       ("font-family", "Inter, sans-serif")]},
            {"selector": "tbody td",
             "props": [("font-family", "Inter, sans-serif"),
                       ("text-align", "right"), ("padding", "10px 8px"),
                       ("font-size", "0.92rem")]},
            {"selector": "tbody tr:hover td",
             "props": [("background-color", "#F0F4FA")]},
            {"selector": "tbody td:first-child",
             "props": [("text-align", "left")]},
        ])
    )


def main() -> None:
    logo_b64 = _img_base64(LOGO)
    hero_b64 = _img_base64(HERO)

    st.markdown(
        '<div class="brand-bar">NEPTUNO COSTA ADEJE &nbsp;|&nbsp; Revenue Dashboard</div>',
        unsafe_allow_html=True,
    )

    cabecera_html = '<div class="brand-header">'
    if logo_b64:
        cabecera_html += f'<img class="logo" src="data:image/png;base64,{logo_b64}" alt="Neptuno Costa Adeje">'
    cabecera_html += (
        '<div class="brand-text">'
        '<h2>Aparthotel Neptuno · Costa Adeje</h2>'
        '<p class="tagline">Your apartment in Costa Adeje · 95 unidades · Tenerife Sur</p>'
        '</div>'
    )
    if hero_b64:
        cabecera_html += f'<img class="hero" src="data:image/jpeg;base64,{hero_b64}" alt="Piscina">'
    cabecera_html += '</div>'
    st.markdown(cabecera_html, unsafe_allow_html=True)

    try:
        almacen = crear_almacen(RAIZ)
        df = cargar_historico(almacen.version())
    except ErrorAlmacen as e:
        st.error(f"**No se puede acceder al histórico.** {e}")
        return

    _seccion_carga(almacen)
    _aviso_caducidad(almacen)

    if df is None or df.empty:
        st.info(
            "Todavía no hay histórico. Sube el primer Excel `Planning de PickUpADR` "
            "en **📥 Cargar el Excel del lunes**, aquí arriba."
        )
        return
    snapshots = sorted(pd.to_datetime(df["Snapshot"]).dt.normalize().unique(), reverse=True)

    with st.sidebar:
        if logo_b64:
            st.markdown(
                f'<img src="data:image/png;base64,{logo_b64}" '
                'style="width:100%;max-width:200px;margin-bottom:1rem">',
                unsafe_allow_html=True,
            )
        st.header("📅 Snapshot")
        seleccion = st.selectbox(
            "Fecha del snapshot",
            options=snapshots,
            format_func=lambda d: pd.Timestamp(d).strftime("%d/%m/%Y (%A)"),
        )
        st.caption(f"{len(snapshots)} snapshot(s) cargado(s).")

        st.divider()
        st.subheader("Pickup mensual")
        ventana_pickup = st.radio(
            "Ventana", options=["día", "semana", "2 semanas"], index=1, horizontal=True,
        )

        st.divider()
        st.subheader("Disponibilidad")
        dias_horizonte = st.slider("Días a mostrar", 7, 60, 30, step=1)

        st.divider()
        st.subheader("Histórico")
        st.caption(almacen.descripcion())
        st.caption(f"Filas totales: {len(df):,}")
        dias_token = almacen.dias_hasta_caducidad()
        if dias_token is not None:
            icono = "🔴" if dias_token <= 7 else ("🟠" if dias_token <= DIAS_AVISO_TOKEN else "🟢")
            st.caption(f"{icono} Credencial: {dias_token} días")

        st.download_button(
            "⬇️ Descargar para Excel",
            data=historico_descargable(almacen.version(), df),
            file_name="historico_neptuno.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            help="El histórico completo, para abrirlo en Excel desde cualquier equipo.",
        )

    snap = pd.Timestamp(seleccion)
    k = kpis_globales(df, snap)

    st.subheader(f"📅 Snapshot del {snap.strftime('%d/%m/%Y (%A)')}")
    st.caption(
        f"Horizonte: **{pd.Timestamp(k['fecha_min']).strftime('%d/%m/%Y')}** → "
        f"**{pd.Timestamp(k['fecha_max']).strftime('%d/%m/%Y')}**  ·  "
        f"{k['dias']} días  ·  {k['dias'] * HABITACIONES_TOTALES:,} room-nights disponibles"
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Producción habitación", f"{k['produccion_total']:,.0f} €",
              delta=_delta_pct(k['produccion_total'], k['produccion_total_ly']),
              help="Suma de Producción Alojamiento (sin bar, F&B ni otros)")
    c2.metric("Reservas totales", f"{k['reservas_totales']:,.0f}",
              delta=_delta_pct(k['reservas_totales'], k['reservas_totales_ly']))
    c3.metric("ADR medio", f"{k['adr']:,.2f} €",
              delta=_delta_pct(k['adr'], k['adr_ly']))
    c4.metric("RevPAR medio", f"{k['revpar']:,.2f} €",
              delta=_delta_pct(k['revpar'], k['revpar_ly']))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ocupación media", f"{k['ocupacion']*100:.1f} %",
              delta=f"{(k['ocupacion'] - k['ocupacion_ly'])*100:+.1f} pp"
              if k['ocupacion_ly'] else None)
    c2.metric("Ocup. próx. 7 días", f"{k['ocup_prox7']*100:.1f} %",
              help=f"{int(k['reservas_prox7'])} reservas / {int(k['noches_prox7'])} noches")
    c3.metric("Pickup semana (total)", f"{k['pickup_semana_total']:+,.0f}")
    c4.metric("Pickup día (total)", f"{k['pickup_dia_total']:+,.0f}")

    # ───── Aviso: días sin el hotel entero a la venta ─────
    bloq = dias_bloqueados(df, snap)
    if not bloq.empty:
        descuadres = int((bloq["Motivo"] != "Habitación fuera de venta").sum())
        noches = int(bloq["Bloqueadas"].sum())
        texto = (
            f"**{len(bloq)} día(s) sin el hotel entero a la venta** en este snapshot "
            f"({noches} noche(s)-habitación bloqueadas), del "
            f"{bloq['Fecha'].iloc[0]} al {bloq['Fecha'].iloc[-1]}. "
            "Van marcados con `*` en los gráficos diarios."
        )
        if descuadres:
            texto += (
                f"  \n⚠️ Ojo: en {descuadres} de ellos el inventario **no cuadra** "
                "(Reservas + Libres + Bloqueadas ≠ 95). Revisa el Excel del PMS."
            )
        st.warning(texto)
        with st.expander(f"Ver los {len(bloq)} días afectados"):
            st.dataframe(bloq, use_container_width=True, hide_index=True)
        st.caption(
            "La ocupación y el RevPAR se siguen calculando sobre las 95 unidades, "
            "igual que el PMS."
        )

    meses = meses_disponibles(df, snap)
    st.divider()

    st.markdown(f"### 🚨 Disponibilidad — próximos {dias_horizonte} días")
    leyenda_html = " &nbsp;·&nbsp; ".join(
        f'<span class="legend-pill" style="background:{c}">{et}</span> '
        f'<span style="font-size:0.85rem;color:{GRAFITO}">'
        f'{0 if i == 0 else UMBRALES_LIBRES[i-1][0]+1}–{lim} libres</span>'
        for i, (lim, et, c) in enumerate(UMBRALES_LIBRES)
    )
    st.markdown(leyenda_html, unsafe_allow_html=True)
    st.plotly_chart(
        grafico_libres_proximo_mes(libres_proximo_mes(df, snap, dias=dias_horizonte)),
        use_container_width=True,
    )

    st.divider()

    st.markdown("### 📈 Pickup neto por mes")
    st.plotly_chart(
        grafico_pickup_mensual(pickup_mensual(df, snap, ventana=ventana_pickup), ventana_pickup),
        use_container_width=True,
    )

    st.markdown("### 💰 Producción mensual de habitación — CY vs LY")
    st.caption("Sólo revenue de **alojamiento** (sin bar, F&B ni otros).")
    st.plotly_chart(
        grafico_produccion_mensual_cy_vs_ly(produccion_mensual_cy_vs_ly(df, snap)),
        use_container_width=True,
    )

    st.divider()

    st.markdown("### 🛏️ Libres CY vs LY  ·  Pickup diario por mes")

    opciones = ["Horizonte completo"] + meses
    sel_col, ventanas_col = st.columns([1, 2])
    with sel_col:
        sel = st.selectbox(
            "Vista",
            options=opciones,
            format_func=lambda x: x if isinstance(x, str) else etiqueta_mes(x),
            key="vista_combinada",
        )
    with ventanas_col:
        ventanas_sel = st.multiselect(
            "Ventanas de pickup (al elegir un mes)",
            options=["Pickup día", "Pickup semana", "Pickup 2 semanas"],
            default=["Pickup día", "Pickup semana", "Pickup 2 semanas"],
            key="pickup_ventanas",
            disabled=(sel == "Horizonte completo"),
        )

    if sel == "Horizonte completo":
        st.plotly_chart(
            grafico_libres_cy_vs_ly(libres_cy_vs_ly(df, snap)),
            use_container_width=True,
        )
        st.caption("👉 Selecciona un mes arriba para ver libres y pickup combinados día a día.")
    else:
        mes_ts = pd.Timestamp(sel)
        st.plotly_chart(
            grafico_libres_pickup_combinado_mes(
                libres_cy_vs_ly_mes(df, snap, mes_ts),
                pickup_diario_mes(df, snap, mes_ts),
                ventanas_sel,
                etiqueta_mes(mes_ts),
            ),
            use_container_width=True,
        )
        st.caption(
            "Eje Y izquierdo: habitaciones libres (líneas).  ·  "
            "Eje Y derecho: pickup en habitaciones (barras)."
        )

    st.divider()

    st.markdown("### 🌊 Pickup por ventana — diario (día / semana / 2 semanas)")
    st.plotly_chart(
        grafico_pickup_por_ventana(pickup_por_ventana(df, snap)),
        use_container_width=True,
    )

    st.divider()

    st.markdown("### 💶 ADR diario — margen para política de precio")
    st.plotly_chart(
        grafico_adr_diario(adr_diario(df, snap)),
        use_container_width=True,
    )

    st.markdown("### 📅 Reservas por mes — CY vs LY")
    st.plotly_chart(
        grafico_reservas_mensuales(reservas_mensuales_cy_vs_ly(df, snap)),
        use_container_width=True,
    )

    st.markdown("### 📊 Tabla mensual — Producción habitación · ADR · Ocupación (CY vs LY)")
    st.caption(
        "🔴 **Filas en rojo claro** = meses críticos con caída ≥ 15 % vs año pasado. "
        "Δ % en verde fuerte si > 5 %, rojo fuerte si ≤ -15 %."
    )
    tabla = tabla_mensual_completa(df, snap)
    st.dataframe(_estilo_tabla(tabla), use_container_width=True, hide_index=True)

    with st.expander("Ver datos brutos del snapshot"):
        st.dataframe(
            df[df["Snapshot"] == snap].reset_index(drop=True),
            use_container_width=True, height=400,
        )


if __name__ == "__main__":
    main()
