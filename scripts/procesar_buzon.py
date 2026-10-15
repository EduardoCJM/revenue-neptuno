"""Procesa los Excel del buzón: los carga al histórico y los archiva por mes/semana.

Uso: doble clic en `Neptuno.bat`, o `python scripts/procesar_buzon.py`.

Si este PC tiene credenciales de GitHub configuradas (en `.streamlit/secrets.toml`
o en variables de entorno), escribe directamente en la nube y así el buzón local
y el dashboard web se mantienen sincronizados. Sin credenciales, trabaja contra
el histórico local.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.ingest.excel_reader import FormatoExcelInvalido
from src.ingest.pipeline import avisos_inventario, procesar_excel
from src.storage.almacen import ErrorAlmacen, crear_almacen

BUZON = RAIZ / "Excel-Lunes" / "BUZON"


def _excels_en_buzon() -> list[Path]:
    if not BUZON.exists():
        return []
    return sorted(p for p in BUZON.glob("*.xlsx") if not p.name.startswith("~$"))


def main() -> int:
    excels = _excels_en_buzon()
    if not excels:
        print("Buzon vacio. No hay Excels que procesar.")
        return 0

    almacen = crear_almacen(RAIZ)
    print(f"Encontrados {len(excels)} archivo(s) en BUZON.")
    print(f"Destino: {almacen.descripcion()}\n")

    ok: list[Path] = []
    ko: list[tuple[Path, str]] = []

    for ruta in excels:
        try:
            res = procesar_excel(ruta.read_bytes(), ruta.name, almacen)
            snapshot = res["snapshot"]
            fecha = snapshot.date() if hasattr(snapshot, "date") else snapshot
            print(
                f"OK  {ruta.name}\n"
                f"    snapshot {fecha}  ->  {res['destino']}\n"
                f"    historico: {res['filas_totales']} filas totales, "
                f"{res['snapshots']} snapshot(s)"
            )
            for aviso in avisos_inventario(res["inventario"], con_acentos=False):
                print(f"    aviso: {aviso}")
            print()

            # Solo se borra del buzon cuando ya esta guardado y archivado.
            ruta.unlink()
            ok.append(ruta)
        except FormatoExcelInvalido as e:
            ko.append((ruta, str(e)))
            print(f"KO  {ruta.name}\n    motivo: {e}\n")
        except ErrorAlmacen as e:
            ko.append((ruta, f"almacen: {e}"))
            print(f"KO  {ruta.name}\n    no se pudo guardar: {e}\n")
        except Exception as e:  # noqa: BLE001
            ko.append((ruta, f"error inesperado: {e}"))
            traceback.print_exc()
            print(f"KO  {ruta.name}\n    {e}\n")

    print("=" * 60)
    print(f"Procesados OK: {len(ok)}    Rechazados: {len(ko)}")
    if ko:
        print()
        print("AVISO: archivos invalidos siguen en BUZON. Revisa los motivos.")
        for ruta, motivo in ko:
            print(f"  - {ruta.name}: {motivo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
