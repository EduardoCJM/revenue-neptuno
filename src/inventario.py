"""Inventario de habitaciones: la invariante del hotel y su aritmética.

El PMS entrega cada día repartido en tres estados que siempre suman el total
del hotel:

    Reservas + Libres + Bloqueadas = 95

`Bloqueadas` son apartamentos fuera de venta (avería, mantenimiento, uso
propio). No son un error del Excel: cuando hay una bloqueada, `Reservas +
Libres` da 94, y eso es correcto.
"""
from __future__ import annotations

import pandas as pd

HABITACIONES_TOTALES = 95
COLUMNA_BLOQUEADAS = "Bloqueadas"

# Margen de cordura sobre el total. Un Excel de otro alojamiento (el de la
# Finca Vistabonita suma 17) queda fuera; un descuadre puntual del PMS entra
# y se marca en el dashboard en lugar de bloquear la carga del lunes.
TOLERANCIA = 2


def bloqueadas(df: pd.DataFrame) -> pd.Series:
    """Habitaciones fuera de venta por día. Ceros si la columna no viene."""
    if COLUMNA_BLOQUEADAS not in df.columns:
        return pd.Series(0.0, index=df.index)
    return df[COLUMNA_BLOQUEADAS].fillna(0).astype(float)


def total_inventario(df: pd.DataFrame) -> pd.Series:
    """Reservas + Libres + Bloqueadas. Debería dar 17 todos los días."""
    return (
        df["Reservas"].fillna(0).astype(float)
        + df["Libres"].fillna(0).astype(float)
        + bloqueadas(df)
    )


def descuadre(df: pd.DataFrame) -> pd.Series:
    """Diferencia respecto al total del hotel. Cero en un día normal, incluso
    con habitaciones bloqueadas. Distinto de cero = el PMS no cuadra."""
    return total_inventario(df) - HABITACIONES_TOTALES
