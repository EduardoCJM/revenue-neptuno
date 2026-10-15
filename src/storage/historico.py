from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.storage.almacen import HOJA_HISTORICO, AlmacenLocal

CLAVE = ["Snapshot", "Fecha"]


def fusionar(df_historico: pd.DataFrame | None,
             df_nuevo: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Añade un snapshot al histórico. Cálculo puro, sin tocar disco.

    Deduplica por `(Snapshot, Fecha)` quedándose con la última aparición, así
    que **volver a cargar el mismo Excel es inocuo**: sobrescribe sus propias
    filas en vez de duplicarlas. De ahí que se pueda recargar sin miedo si la
    nube y el local se desincronizan.
    """
    if df_historico is None or df_historico.empty:
        filas_previas = 0
        df = df_nuevo.copy()
    else:
        filas_previas = len(df_historico)
        df = pd.concat([df_historico, df_nuevo], ignore_index=True)
        df = df.drop_duplicates(subset=CLAVE, keep="last").reset_index(drop=True)

    df = df.sort_values(CLAVE).reset_index(drop=True)

    return df, {
        "filas_previas": filas_previas,
        "filas_nuevas": len(df_nuevo),
        "filas_totales": len(df),
        "snapshots": df["Snapshot"].dropna().nunique(),
    }


def guardar_snapshot(df_nuevo: pd.DataFrame, ruta_historico: str | Path) -> dict:
    """Carga un snapshot en un histórico local concreto.

    Se mantiene para `scripts/cargar_semana.py`, que apunta a una ruta dada.
    El flujo normal usa `src.ingest.pipeline.procesar_excel()`.
    """
    ruta = Path(ruta_historico)
    almacen = AlmacenLocal(ruta.parent.parent.parent)
    almacen.ruta_historico = ruta

    df, info = fusionar(almacen.leer_historico(), df_nuevo)
    almacen.escribir_historico(df, "Carga manual")
    return {"ruta": str(ruta), **info}


__all__ = ["CLAVE", "HOJA_HISTORICO", "fusionar", "guardar_snapshot"]
