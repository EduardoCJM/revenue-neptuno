from __future__ import annotations

import pandas as pd

from src.inventario import HABITACIONES_TOTALES, bloqueadas, descuadre
from src.ui.tema import DORADO_ARENA, UMBRALES_LIBRES, color_por_libres, color_pickup

MESES_ES = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
}
DIAS_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def _filtrar_snapshot(df: pd.DataFrame, snapshot: pd.Timestamp) -> pd.DataFrame:
    sub = df[df["Snapshot"] == snapshot].copy()
    sub["Fecha"] = pd.to_datetime(sub["Fecha"])
    return sub.sort_values("Fecha").reset_index(drop=True)


def _agregar_mes(sub: pd.DataFrame) -> pd.Series:
    return sub["Fecha"].dt.to_period("M").dt.to_timestamp()


# ─────────── Días con inventario incompleto ───────────

def _marcar_inventario(sub: pd.DataFrame) -> pd.DataFrame:
    """Añade `Bloqueadas`, `Descuadre`, `Marcado` y `Nota` a un sub-snapshot."""
    sub["Bloqueadas"] = bloqueadas(sub)
    sub["Descuadre"] = descuadre(sub)
    sub["Marcado"] = (sub["Bloqueadas"] > 0) | (sub["Descuadre"] != 0)
    sub["Nota"] = sub.apply(lambda r: _nota_inventario(r["Bloqueadas"], r["Descuadre"]), axis=1)
    return sub


def _nota_inventario(bloq: float, desc: float) -> str:
    """Línea extra para el hover. Cadena vacía si el día es normal."""
    partes = []
    if bloq > 0:
        n = int(bloq)
        partes.append(f"{n} habitación fuera de venta" if n == 1
                      else f"{n} habitaciones fuera de venta")
    if desc != 0:
        partes.append(f"inventario descuadrado ({int(desc):+d} hab.)")
    if not partes:
        return ""
    return f"<br><b>* {' · '.join(partes)}</b>"


def _asterisco(marcado: bool) -> str:
    if not marcado:
        return ""
    return f"<span style='color:{DORADO_ARENA};font-weight:700'>*</span>"


def _etiqueta_dia_mes(fecha: pd.Timestamp, dia_semana: str, marcado: bool) -> str:
    """Etiqueta del eje X para los gráficos de un mes concreto.

    Es también la CLAVE DE CATEGORÍA del eje: el gráfico combinado alinea las
    barras de pickup con las líneas de libres comparando esta cadena. Por eso
    la generan aquí `libres_cy_vs_ly_mes` y `pickup_diario_mes` en vez de
    escribirla cada una por su lado — si difirieran, el eje se duplicaría.
    """
    return (
        f"<b style='font-size:13px'>{fecha.strftime('%d/%m')}{_asterisco(marcado)}</b><br>"
        f"<span style='font-size:11px;color:#6B7280'>{dia_semana}</span>"
    )


def dias_bloqueados(df: pd.DataFrame, snapshot: pd.Timestamp) -> pd.DataFrame:
    """Días del snapshot que no tenían el hotel entero a la venta."""
    sub = _marcar_inventario(_filtrar_snapshot(df, snapshot))
    sub = sub[sub["Marcado"]]
    if sub.empty:
        return pd.DataFrame(columns=["Fecha", "Día", "Bloqueadas", "Libres", "Reservas", "Motivo"])
    return pd.DataFrame(
        {
            "Fecha": sub["Fecha"].dt.strftime("%d/%m/%Y"),
            "Día": sub["Fecha"].dt.weekday.map(lambda i: DIAS_ES[i]),
            "Bloqueadas": sub["Bloqueadas"].astype(int),
            "Libres": sub["Libres"].astype(int),
            "Reservas": sub["Reservas"].astype(int),
            "Motivo": sub.apply(
                lambda r: "Habitación fuera de venta" if r["Descuadre"] == 0
                else f"Inventario descuadrado ({int(r['Descuadre']):+d} hab.)",
                axis=1,
            ),
        }
    ).reset_index(drop=True)


def libres_cy_vs_ly(df: pd.DataFrame, snapshot: pd.Timestamp) -> pd.DataFrame:
    sub = _filtrar_snapshot(df, snapshot)
    libres_ly = HABITACIONES_TOTALES - sub["Reservas año anterior"].fillna(0).clip(upper=HABITACIONES_TOTALES)
    return pd.DataFrame(
        {
            "Fecha": sub["Fecha"],
            "Libres CY": sub["Libres"].astype(float),
            "Libres LY": libres_ly.astype(float),
        }
    )


def libres_cy_vs_ly_mes(df: pd.DataFrame, snapshot: pd.Timestamp,
                        mes: pd.Timestamp) -> pd.DataFrame:
    """Libres CY vs LY filtrado a un mes, con etiquetas claras día a día."""
    sub = _filtrar_snapshot(df, snapshot)
    inicio = pd.Timestamp(mes).normalize().replace(day=1)
    fin = inicio + pd.offsets.MonthBegin(1)
    sub = sub[(sub["Fecha"] >= inicio) & (sub["Fecha"] < fin)].copy()

    libres_ly = HABITACIONES_TOTALES - sub["Reservas año anterior"].fillna(0).clip(upper=HABITACIONES_TOTALES)
    sub["Día semana"] = sub["Fecha"].dt.weekday.map(lambda i: DIAS_ES[i])
    sub["Weekday num"] = sub["Fecha"].dt.weekday
    sub["Es finde"] = sub["Weekday num"] >= 4
    sub = _marcar_inventario(sub)
    sub["Etiqueta multilinea"] = sub.apply(
        lambda r: _etiqueta_dia_mes(r["Fecha"], r["Día semana"], r["Marcado"]), axis=1,
    )
    return pd.DataFrame(
        {
            "Fecha": sub["Fecha"],
            "Etiqueta multilinea": sub["Etiqueta multilinea"],
            "Día semana": sub["Día semana"],
            "Es finde": sub["Es finde"],
            "Libres CY": sub["Libres"].astype(float),
            "Libres LY": libres_ly.astype(float),
            "Reservas CY": sub["Reservas"].astype(float),
            "Reservas LY": sub["Reservas año anterior"].fillna(0).astype(float),
            "Bloqueadas": sub["Bloqueadas"],
            "Nota": sub["Nota"],
        }
    )


def libres_proximo_mes(df: pd.DataFrame, snapshot: pd.Timestamp, dias: int = 30) -> pd.DataFrame:
    sub = _filtrar_snapshot(df, snapshot)
    sub = sub[sub["Fecha"] < (snapshot + pd.Timedelta(days=dias))].copy()
    sub["Día semana"] = sub["Fecha"].dt.weekday.map(lambda i: DIAS_ES[i])
    sub["Weekday num"] = sub["Fecha"].dt.weekday
    sub["Es finde"] = sub["Weekday num"] >= 4  # Vie, Sáb, Dom
    sub = _marcar_inventario(sub)
    inicial_semana = ["L", "M", "X", "J", "V", "S", "D"]

    def _etiqueta(r):
        es_primer = r["Fecha"].day == 1 or r["Fecha"] == sub["Fecha"].iloc[0]
        dia_txt = r["Fecha"].strftime("%d/%m") if es_primer else f"{r['Fecha'].day:02d}"
        weight = 700 if r["Fecha"].weekday() == 0 or es_primer else 500
        ini = inicial_semana[r["Fecha"].weekday()]
        return (
            f"<span style='font-size:12px;font-weight:{weight};color:#1F2937'>"
            f"{dia_txt}{_asterisco(r['Marcado'])}</span><br>"
            f"<span style='font-size:10px;color:#9CA3AF'>{ini}</span>"
        )

    sub["Etiqueta multilinea"] = sub.apply(_etiqueta, axis=1)
    sub["Color"] = sub["Libres"].apply(color_por_libres)
    return pd.DataFrame(
        {
            "Fecha": sub["Fecha"],
            "Etiqueta multilinea": sub["Etiqueta multilinea"],
            "Día semana": sub["Día semana"],
            "Weekday num": sub["Weekday num"],
            "Es finde": sub["Es finde"],
            "Libres": sub["Libres"].astype(float),
            "Reservas": sub["Reservas"].astype(float),
            "Color": sub["Color"],
            "Bloqueadas": sub["Bloqueadas"],
            "Nota": sub["Nota"],
        }
    )


def reservas_mensuales_cy_vs_ly(df: pd.DataFrame, snapshot: pd.Timestamp) -> pd.DataFrame:
    sub = _filtrar_snapshot(df, snapshot)
    sub["Mes"] = _agregar_mes(sub)
    agg = (
        sub.groupby("Mes", as_index=False)
        .agg(
            **{
                "Reservas CY": ("Reservas", "sum"),
                "Reservas LY": ("Reservas año anterior", "sum"),
            }
        )
        .sort_values("Mes")
    )
    agg["Etiqueta"] = agg["Mes"].apply(lambda d: f"{MESES_ES[d.month]} {d.year}")
    return agg


def meses_disponibles(df: pd.DataFrame, snapshot: pd.Timestamp) -> list[pd.Timestamp]:
    """Lista de inicios de mes presentes en el horizonte del snapshot, ordenada."""
    sub = _filtrar_snapshot(df, snapshot)
    meses = sorted(sub["Fecha"].dt.to_period("M").dt.to_timestamp().unique())
    return [pd.Timestamp(m) for m in meses]


def etiqueta_mes(mes: pd.Timestamp) -> str:
    return f"{MESES_ES[mes.month]} {mes.year}"


def pickup_diario_mes(df: pd.DataFrame, snapshot: pd.Timestamp,
                      mes: pd.Timestamp) -> pd.DataFrame:
    """Pickup día/semana/2 semanas por fecha de estancia, filtrado a un mes."""
    sub = _filtrar_snapshot(df, snapshot)
    inicio = pd.Timestamp(mes).normalize().replace(day=1)
    fin = (inicio + pd.offsets.MonthBegin(1))
    sub = sub[(sub["Fecha"] >= inicio) & (sub["Fecha"] < fin)].copy()
    sub["Día semana"] = sub["Fecha"].dt.weekday.map(lambda i: DIAS_ES[i])
    sub["Weekday num"] = sub["Fecha"].dt.weekday
    sub["Es finde"] = sub["Weekday num"] >= 4
    sub = _marcar_inventario(sub)
    sub["Etiqueta multilinea"] = sub.apply(
        lambda r: _etiqueta_dia_mes(r["Fecha"], r["Día semana"], r["Marcado"]), axis=1,
    )
    return pd.DataFrame(
        {
            "Fecha": sub["Fecha"],
            "Etiqueta multilinea": sub["Etiqueta multilinea"],
            "Día semana": sub["Día semana"],
            "Weekday num": sub["Weekday num"],
            "Es finde": sub["Es finde"],
            "Pickup día": sub["Pickup día anterior"].fillna(0).astype(float),
            "Pickup semana": sub["Pickup semana anterior"].fillna(0).astype(float),
            "Pickup 2 semanas": sub["Pickup 2 semanas anteriores"].fillna(0).astype(float),
        }
    )


def pickup_por_ventana(df: pd.DataFrame, snapshot: pd.Timestamp) -> pd.DataFrame:
    sub = _filtrar_snapshot(df, snapshot)
    return pd.DataFrame(
        {
            "Fecha": sub["Fecha"],
            "Pickup día": sub["Pickup día anterior"].fillna(0).astype(float),
            "Pickup semana": sub["Pickup semana anterior"].fillna(0).astype(float),
            "Pickup 2 semanas": sub["Pickup 2 semanas anteriores"].fillna(0).astype(float),
        }
    )


COLUMNA_PICKUP = {
    "día": "Pickup día anterior",
    "semana": "Pickup semana anterior",
    "2 semanas": "Pickup 2 semanas anteriores",
}


def pickup_mensual(df: pd.DataFrame, snapshot: pd.Timestamp, ventana: str = "semana") -> pd.DataFrame:
    if ventana not in COLUMNA_PICKUP:
        raise ValueError(f"Ventana desconocida: {ventana}. Opciones: {list(COLUMNA_PICKUP)}")
    columna = COLUMNA_PICKUP[ventana]
    sub = _filtrar_snapshot(df, snapshot)
    sub["Mes"] = _agregar_mes(sub)
    agg = (
        sub.groupby("Mes", as_index=False)[columna]
        .sum()
        .rename(columns={columna: "Pickup neto"})
        .sort_values("Mes")
    )
    agg["Etiqueta"] = agg["Mes"].apply(lambda d: f"{MESES_ES[d.month]} {d.year}")
    return agg


def adr_diario(df: pd.DataFrame, snapshot: pd.Timestamp) -> pd.DataFrame:
    """ADR alojamiento por día de estancia + ADR LY como referencia."""
    sub = _filtrar_snapshot(df, snapshot)
    return pd.DataFrame(
        {
            "Fecha": sub["Fecha"],
            "Día semana": sub["Fecha"].dt.weekday.map(lambda i: DIAS_ES[i]),
            "ADR aloj. CY": sub["ADR alojamiento"].astype(float),
            "ADR aloj. LY": sub["ADR aloj. año anterior"].astype(float),
            "ADR Total CY": sub["ADR Total"].astype(float),
            "Reservas": sub["Reservas"].astype(float),
        }
    )


def produccion_mensual_cy_vs_ly(df: pd.DataFrame, snapshot: pd.Timestamp) -> pd.DataFrame:
    """Producción ALOJAMIENTO (revenue de habitación, sin bar/F&B/Otros)."""
    sub = _filtrar_snapshot(df, snapshot)
    sub["Mes"] = _agregar_mes(sub)
    agg = (
        sub.groupby("Mes", as_index=False)
        .agg(
            **{
                "Producción CY": ("Producción Alojamiento", "sum"),
                "Producción LY": ("Producción Alojamiento año anterior", "sum"),
            }
        )
        .sort_values("Mes")
    )
    agg["Δ €"] = agg["Producción CY"] - agg["Producción LY"]
    agg["Δ %"] = (agg["Δ €"] / agg["Producción LY"].replace(0, pd.NA)) * 100
    agg["Etiqueta"] = agg["Mes"].apply(lambda d: f"{MESES_ES[d.month]} {d.year}")
    return agg


def tabla_mensual_completa(df: pd.DataFrame, snapshot: pd.Timestamp) -> pd.DataFrame:
    """Tabla mensual con Producción Alojamiento, ADR y Ocupación CY vs LY."""
    sub = _filtrar_snapshot(df, snapshot)
    sub["Mes"] = _agregar_mes(sub)

    rows = []
    for mes, g in sub.groupby("Mes"):
        noches_disp = HABITACIONES_TOTALES * len(g)
        # Producción de habitación (alojamiento), no total
        prod_cy = float(g["Producción Alojamiento"].sum())
        prod_ly = float(g["Producción Alojamiento año anterior"].sum())
        res_cy = float(g["Reservas"].sum())
        res_ly = float(g["Reservas año anterior"].sum())
        # ADR = revenue habitación / habitaciones vendidas (consistente CY y LY)
        adr_cy = prod_cy / res_cy if res_cy else 0.0
        adr_ly = prod_ly / res_ly if res_ly else 0.0
        ocup_cy = res_cy / noches_disp if noches_disp else 0.0
        ocup_ly = res_ly / noches_disp if noches_disp else 0.0

        rows.append(
            {
                "Mes": f"{MESES_ES[mes.month]} {mes.year}",
                "Producción CY (€)": prod_cy,
                "Producción LY (€)": prod_ly,
                "Δ Producción (€)": prod_cy - prod_ly,
                "Δ Producción (%)": ((prod_cy - prod_ly) / prod_ly * 100) if prod_ly else None,
                "ADR CY (€)": adr_cy,
                "ADR LY (€)": adr_ly,
                "Δ ADR (€)": adr_cy - adr_ly,
                "Δ ADR (%)": ((adr_cy - adr_ly) / adr_ly * 100) if adr_ly else None,
                "Ocup CY (%)": ocup_cy * 100,
                "Ocup LY (%)": ocup_ly * 100,
                "Δ Ocup (pp)": (ocup_cy - ocup_ly) * 100,
            }
        )
    return pd.DataFrame(rows)


def kpis_globales(df: pd.DataFrame, snapshot: pd.Timestamp) -> dict:
    sub = _filtrar_snapshot(df, snapshot)
    noches_disp = HABITACIONES_TOTALES * len(sub)

    reservas_cy = float(sub["Reservas"].sum())
    reservas_ly = float(sub["Reservas año anterior"].sum())
    # Producción ALOJAMIENTO (revenue de habitación, sin bar/F&B)
    prod_cy = float(sub["Producción Alojamiento"].sum())
    prod_ly = float(sub["Producción Alojamiento año anterior"].sum())

    ocupacion = reservas_cy / noches_disp if noches_disp else 0.0
    ocupacion_ly = reservas_ly / noches_disp if noches_disp else 0.0
    adr = prod_cy / reservas_cy if reservas_cy else 0.0
    adr_ly = prod_ly / reservas_ly if reservas_ly else 0.0
    revpar = prod_cy / noches_disp if noches_disp else 0.0
    revpar_ly = prod_ly / noches_disp if noches_disp else 0.0

    prox7 = sub[sub["Fecha"] < (snapshot + pd.Timedelta(days=7))]
    libres_prox7 = float(prox7["Libres"].sum())
    reservas_prox7 = float(prox7["Reservas"].sum())
    noches_prox7 = HABITACIONES_TOTALES * len(prox7)
    ocup_prox7 = reservas_prox7 / noches_prox7 if noches_prox7 else 0.0

    pickup_dia_total = float(sub["Pickup día anterior"].fillna(0).sum())
    pickup_semana_total = float(sub["Pickup semana anterior"].fillna(0).sum())

    return {
        "snapshot": snapshot,
        "fecha_min": sub["Fecha"].min(),
        "fecha_max": sub["Fecha"].max(),
        "dias": len(sub),
        "ocupacion": ocupacion,
        "ocupacion_ly": ocupacion_ly,
        "adr": adr,
        "adr_ly": adr_ly,
        "revpar": revpar,
        "revpar_ly": revpar_ly,
        "produccion_total": prod_cy,
        "produccion_total_ly": prod_ly,
        "reservas_totales": reservas_cy,
        "reservas_totales_ly": reservas_ly,
        "libres_prox7": libres_prox7,
        "reservas_prox7": reservas_prox7,
        "ocup_prox7": ocup_prox7,
        "noches_prox7": noches_prox7,
        "pickup_dia_total": pickup_dia_total,
        "pickup_semana_total": pickup_semana_total,
    }


def resumen_mensual(df: pd.DataFrame, snapshot: pd.Timestamp) -> pd.DataFrame:
    return produccion_mensual_cy_vs_ly(df, snapshot)
