from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import IO, Any

import pandas as pd

from src.inventario import (
    HABITACIONES_TOTALES,
    TOLERANCIA,
    bloqueadas,
    descuadre,
    total_inventario,
)

HOJA_ESPERADA = "Planning de PickUpADR"
COLUMNAS_ESPERADAS = 149
TIPO_FILTRO_ESPERADO = "Allotment"


class FormatoExcelInvalido(Exception):
    pass


def leer_snapshot(origen: str | Path | bytes | IO[bytes],
                  nombre: str | None = None) -> pd.DataFrame:
    """Lee y valida un Excel del PMS.

    `origen` puede ser una ruta en disco o el contenido en memoria (bytes o un
    objeto tipo fichero), que es como llega un Excel subido desde el navegador.
    Con contenido en memoria hay que pasar `nombre`, que es lo que se guarda en
    la columna `Archivo Origen` y lo que aparece en los mensajes de error.
    """
    if isinstance(origen, (str, Path)):
        ruta = Path(origen)
        if not ruta.exists():
            raise FileNotFoundError(f"No existe el archivo: {ruta}")
        entrada: Any = ruta
        nombre = nombre or ruta.name
    else:
        entrada = BytesIO(origen) if isinstance(origen, bytes) else origen
        if not nombre:
            raise ValueError("Hace falta `nombre` al leer un Excel en memoria.")

    df = pd.read_excel(entrada, sheet_name=HOJA_ESPERADA)

    _validar(df, nombre)

    fecha_snapshot = pd.to_datetime(df["Fecha Inicial"].iloc[0]).normalize()
    meta = pd.DataFrame(
        {
            "Snapshot": [fecha_snapshot] * len(df),
            "Archivo Origen": [nombre] * len(df),
        }
    )
    return pd.concat([meta, df.reset_index(drop=True)], axis=1)


def _validar(df: pd.DataFrame, nombre: str) -> None:
    if len(df.columns) != COLUMNAS_ESPERADAS:
        raise FormatoExcelInvalido(
            f"{nombre}: se esperaban {COLUMNAS_ESPERADAS} columnas, "
            f"llegaron {len(df.columns)}."
        )

    tipos = df["Tipo de Filtro"].dropna().unique().tolist()
    if tipos != [TIPO_FILTRO_ESPERADO]:
        raise FormatoExcelInvalido(
            f"{nombre}: se esperaba Tipo de Filtro='{TIPO_FILTRO_ESPERADO}', "
            f"llegaron {tipos}."
        )

    # Inventario: Reservas + Libres + Bloqueadas debe dar el total del hotel,
    # todos los días. Un día con habitaciones bloqueadas cuadra igual, así que
    # no rechaza el Excel; solo se rechaza lo que no puede ser del Neptuno.
    total = total_inventario(df)
    fuera = total[(total - HABITACIONES_TOTALES).abs() > TOLERANCIA]
    if not fuera.empty:
        valores = sorted({int(v) for v in fuera.unique()})
        raise FormatoExcelInvalido(
            f"{nombre}: inventario de {valores} habitaciones en "
            f"{len(fuera)} de {len(df)} filas; se esperaban "
            f"{HABITACIONES_TOTALES} (+-{TOLERANCIA}). "
            f"Es un Excel de otro hotel?"
        )


def resumen_inventario(df: pd.DataFrame) -> dict:
    """Días con habitaciones fuera de venta o con el inventario descuadrado.

    Sirve para avisar por consola tras una carga correcta: el Excel entra,
    pero conviene saber que esos días no tenían el hotel entero a la venta.
    """
    bloq = bloqueadas(df)
    desc = descuadre(df)
    fechas = pd.to_datetime(df["Fecha"])

    con_bloqueo = bloq > 0
    con_descuadre = desc != 0

    return {
        "dias_bloqueados": int(con_bloqueo.sum()),
        "roomnights_bloqueadas": int(bloq.sum()),
        "fechas_bloqueadas": sorted(fechas[con_bloqueo].dt.date.tolist()),
        "dias_descuadre": int(con_descuadre.sum()),
        "fechas_descuadre": sorted(fechas[con_descuadre].dt.date.tolist()),
    }
