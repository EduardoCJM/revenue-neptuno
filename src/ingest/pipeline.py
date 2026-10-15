"""La ingesta de un Excel, de principio a fin.

Único camino: lo usan tanto la subida desde el navegador (`app.py`) como el
buzón local (`scripts/procesar_buzon.py`), así que no hay dos comportamientos
que puedan divergir.
"""
from __future__ import annotations

import pandas as pd

from src.ingest.excel_reader import leer_snapshot, resumen_inventario
from src.storage.almacen import Almacen
from src.storage.historico import fusionar


def procesar_excel(datos: bytes, nombre: str, almacen: Almacen) -> dict:
    """Valida un Excel, lo añade al histórico y archiva el original.

    Lanza `FormatoExcelInvalido` si el Excel no es del Neptuno, y `ErrorAlmacen`
    si falla la escritura. En ambos casos no deja nada a medias: el histórico
    solo se escribe cuando la validación ya ha pasado.
    """
    df_nuevo = leer_snapshot(datos, nombre=nombre)
    snapshot = df_nuevo["Snapshot"].iloc[0]

    df, info = fusionar(almacen.leer_historico(), df_nuevo)

    fecha = snapshot.date() if hasattr(snapshot, "date") else snapshot
    almacen.escribir_historico(df, f"Snapshot {fecha} ({nombre})")

    # El original se archiva DESPUES del histórico: si esto falla, el dato ya
    # está salvado y basta con volver a subir el Excel (la deduplicación por
    # (Snapshot, Fecha) hace que recargar sea inocuo).
    destino = almacen.archivar_excel(nombre, datos, snapshot)

    return {
        "nombre": nombre,
        "snapshot": snapshot,
        "destino": destino,
        "inventario": resumen_inventario(df_nuevo),
        **info,
    }


def avisos_inventario(inv: dict, con_acentos: bool = True) -> list[str]:
    """Avisos legibles sobre días sin el hotel entero a la venta.

    `con_acentos=False` para la consola de Windows, que es CP1252 y no los
    soporta.
    """
    def _rango(fechas) -> str:
        if len(fechas) == 1:
            return fechas[0].strftime("%d/%m")
        return f"{fechas[0].strftime('%d/%m')}-{fechas[-1].strftime('%d/%m')}"

    avisos = []
    if inv["dias_bloqueados"]:
        texto = (
            f"{inv['dias_bloqueados']} dia(s) con habitaciones fuera de venta "
            f"({_rango(inv['fechas_bloqueadas'])}), "
            f"{inv['roomnights_bloqueadas']} noche(s)-habitacion."
        )
        avisos.append(
            texto.replace("dia(s)", "día(s)").replace("noche(s)-habitacion",
                                                      "noche(s)-habitación")
            if con_acentos else texto
        )
    if inv["dias_descuadre"]:
        texto = (
            f"{inv['dias_descuadre']} dia(s) con el inventario descuadrado "
            f"({_rango(inv['fechas_descuadre'])}). Se cargan igual, marcados "
            f"en el dashboard."
        )
        avisos.append(texto.replace("dia(s)", "día(s)") if con_acentos else texto)
    return avisos
