from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.ingest.excel_reader import FormatoExcelInvalido, leer_snapshot
from src.storage.historico import guardar_snapshot

HISTORICO_DEFECTO = RAIZ / "data" / "historico" / "historico_neptuno.xlsx"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Carga un Excel semanal de Neptuno Costa Adeje en el historico."
    )
    parser.add_argument(
        "excel",
        type=Path,
        help="Ruta al Excel Planning de PickUpADR de la semana a cargar.",
    )
    parser.add_argument(
        "--historico",
        type=Path,
        default=HISTORICO_DEFECTO,
        help=f"Ruta al historico maestro (por defecto: {HISTORICO_DEFECTO.relative_to(RAIZ)}).",
    )
    args = parser.parse_args()

    try:
        df = leer_snapshot(args.excel)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 1
    except FormatoExcelInvalido as e:
        print(f"ERROR de formato: {e}")
        return 2

    snapshot = df["Snapshot"].iloc[0].date()
    print(f"Leido {args.excel.name}: {len(df)} filas, snapshot {snapshot}.")

    info = guardar_snapshot(df, args.historico)
    print(
        f"Historico actualizado en {info['ruta']}:\n"
        f"  filas previas:  {info['filas_previas']}\n"
        f"  filas nuevas:   {info['filas_nuevas']}\n"
        f"  filas totales:  {info['filas_totales']}\n"
        f"  snapshots:      {info['snapshots']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
