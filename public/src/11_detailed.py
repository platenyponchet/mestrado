"""
process_energy_csv11.py
-----------------------
Lê um CSV com coluna 'utc_timestamp' (datetime ISO 8601 UTC) e múltiplas
colunas de medição. O usuário escolhe qual coluna usar como mains via argumento.
Dados já em resolução de 1 minuto.
Encontra a primeira meia-noite UTC e gera até 7 arquivos JSON com os dias completos.

Uso:
    python process_energy_csv11.py <caminho_do_csv> --column <nome_da_coluna> [--prefix PREFIXO]

Exemplo:
    python process_energy_csv11.py dados.csv --column DE_KN_residential3_grid_import --prefix 01
"""

import sys
import json
import pandas as pd
from pathlib import Path


def load_and_prepare(csv_path: Path, mains_col: str) -> pd.Series:
    """Lê o CSV, usa a coluna indicada como mains e reamostra para 1 minuto."""
    df = pd.read_csv(csv_path, na_values=["", "NULL", "null"])

    if "utc_timestamp" not in df.columns:
        raise ValueError("Coluna 'utc_timestamp' não encontrada no arquivo.")
    if mains_col not in df.columns:
        raise ValueError(f"Coluna '{mains_col}' não encontrada no arquivo.")

    df["datetime"] = pd.to_datetime(df["utc_timestamp"], utc=True)
    df = df.sort_values("datetime").set_index("datetime")

    df[mains_col] = pd.to_numeric(df[mains_col], errors="coerce")

    # Calcula deltas (dados cumulativos → consumo por minuto)
    # diff() negativo indica reset do contador — descarta esses pontos
    df[mains_col] = df[mains_col].diff() * 1000
    df.loc[df[mains_col] < 0, mains_col] = None

    # Reamostra para garantir índice regular de 1 minuto
    series = df[mains_col].resample("1min").mean()
    return series


def find_first_midnight(series: pd.Series) -> pd.Timestamp | None:
    """Retorna o primeiro índice com horário exatamente 00:00:00 UTC."""
    midnight_mask = (
        (series.index.hour == 0)
        & (series.index.minute == 0)
        & (series.index.second == 0)
    )
    candidates = series.index[midnight_mask]
    return candidates[0] if len(candidates) > 0 else None


def extract_complete_days(
    series: pd.Series,
    start: pd.Timestamp,
    max_days: int = 7,
) -> list[tuple[pd.Timestamp, list]]:
    complete_days = []
    current = start

    while len(complete_days) < max_days:
        expected_index = pd.date_range(start=current, periods=1440, freq="1min", tz="UTC")
        day_data = series.reindex(expected_index)

        if not day_data.isna().any():
            values = [round(float(v), 4) for v in day_data]
            complete_days.append((current, values))
        else:
            missing = day_data.isna().sum()
            print(f"  ⚠ Dia {current.date()} ignorado ({missing} minuto(s) ausente(s))")

        current += pd.Timedelta(days=1)

        if current > series.index[-1]:
            break

    return complete_days


def save_json_files(
    complete_days: list[tuple[pd.Timestamp, list]],
    original_name: str,
    first_midnight: pd.Timestamp,
    output_dir: Path,
) -> None:
    date_inicio = first_midnight.strftime("%d-%m-%Y")

    for day_ts, values in complete_days:
        date_do_dia = day_ts.strftime("%Y-%m-%d")
        filename = f"{original_name}--{date_inicio}--{date_do_dia}.json"
        out_path = output_dir / filename

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(values, f, separators=(",", ":"))

        print(f"  ✔ Salvo: {filename}  ({len(values)} valores)")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Processa CSV com utc_timestamp e coluna mains escolhida pelo usuário."
    )
    parser.add_argument("csv", type=Path, help="Caminho do arquivo CSV")
    parser.add_argument("--column", type=str, required=True, help="Nome da coluna a usar como mains")
    parser.add_argument("--prefix", type=str, default="", help="Prefixo para os arquivos de saída (ex: 01)")
    args = parser.parse_args()

    csv_path = args.csv.resolve()
    if not csv_path.exists():
        print(f"Erro: arquivo não encontrado — {csv_path}")
        sys.exit(1)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    stem = csv_path.stem
    original_name = f"{args.prefix}_{stem}" if args.prefix else stem

    print(f"\n📂 Arquivo: {csv_path.name}" + (f"  (prefixo: {args.prefix})" if args.prefix else ""))
    print(f"   Coluna mains: {args.column}")

    print("⏳ Carregando dados...")
    series = load_and_prepare(csv_path, args.column)
    print(f"   Intervalo: {series.index[0]}  →  {series.index[-1]}")
    print(f"   Total de minutos: {len(series)}")

    first_midnight = find_first_midnight(series)
    if first_midnight is None:
        print("❌ Nenhuma meia-noite (00:00:00 UTC) encontrada nos dados.")
        sys.exit(1)
    print(f"🕛 Primeira meia-noite: {first_midnight}")

    print("🔍 Procurando dias completos (1440 min sem ausências)...")
    complete_days = extract_complete_days(series, first_midnight, max_days=7)

    if not complete_days:
        print("⚠️  Nenhum dia completo encontrado.")
        sys.exit(0)

    print(f"✅ {len(complete_days)} dia(s) completo(s) encontrado(s).\n")

    save_json_files(complete_days, original_name, first_midnight, output_dir)

    print(f"\n🎉 Concluído! Arquivos salvos em: {output_dir}")


if __name__ == "__main__":
    main()