"""
process_energy_csv4.py
----------------------
Lê um CSV no formato GREEND (timestamp Unix float em segundos + colunas por
endereço MAC ZigBee). Identifica automaticamente a coluna com maior amplitude
(max - min) como proxy de "mains", reamostra para 1 minuto, encontra a
primeira meia-noite e gera até 7 arquivos JSON com os dias completos.

Uso:
    python process_energy_csv4.py <caminho_do_csv> [--prefix PREFIXO]
    python process_energy_csv4.py <caminho_do_csv> --list-columns
"""

import sys
import json
import math
import pandas as pd
from pathlib import Path


def load_csv(csv_path: Path) -> pd.DataFrame:
    """Lê o CSV tratando NULL e valores ausentes."""
    df = pd.read_csv(csv_path, na_values=["NULL", "null", "NaN", "nan", ""])
    return df


def pick_mains_column(df: pd.DataFrame, timestamp_col: str) -> str:
    """Retorna a primeira coluna de dados (excluindo o timestamp)."""
    candidates = [c for c in df.columns if c != timestamp_col]
    if not candidates:
        raise ValueError("Nenhuma coluna de dados encontrada além do timestamp.")
    chosen = candidates[0]
    print(f"\n   Coluna selecionada (primeira): {chosen}")
    return chosen


def load_and_prepare(csv_path: Path) -> tuple[pd.Series, str]:
    """
    Carrega o CSV, seleciona a coluna de maior amplitude como mains,
    converte o timestamp e reamostra para 1 minuto.
    Retorna a série reamostrada e o nome da coluna escolhida.
    """
    df = load_csv(csv_path)

    # Detecta coluna de timestamp pelo nome ou, como fallback, a primeira coluna
    if "timestamp" in df.columns:
        timestamp_col = "timestamp"
    else:
        timestamp_col = df.columns[0]

    # Converte timestamp (segundos float → datetime UTC)
    df[timestamp_col] = pd.to_datetime(df[timestamp_col], unit="s", utc=True)
    df = df.sort_values(timestamp_col).set_index(timestamp_col)

    # Converte todas as colunas de dados para numérico
    df = df.apply(pd.to_numeric, errors="coerce")

    mains_col = pick_mains_column(df.reset_index(), timestamp_col)

    series = df[mains_col].resample("1min").mean()
    return series, mains_col


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
    """
    A partir de 'start', percorre dia a dia e coleta os dias com 1440 valores
    sem nenhum NaN. Dias incompletos são ignorados.
    """
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
    """Salva cada dia como um arquivo JSON."""
    date_inicio = first_midnight.strftime("%d-%m-%Y")

    for day_ts, values in complete_days:
        date_do_dia = day_ts.strftime("%Y-%m-%d")
        filename = f"{original_name}--{date_inicio}--{date_do_dia}.json"
        out_path = output_dir / filename

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(values, f, separators=(",", ":"))

        print(f"  ✔ Salvo: {filename}  ({len(values)} valores)")


def list_columns(csv_path: Path) -> None:
    """Imprime as colunas disponíveis e suas amplitudes."""
    df = load_csv(csv_path)
    timestamp_col = "timestamp" if "timestamp" in df.columns else df.columns[0]
    numeric = df.drop(columns=[timestamp_col]).apply(pd.to_numeric, errors="coerce")
    amplitudes = (numeric.max() - numeric.min()).dropna().sort_values(ascending=False)

    print(f"\nColunas em '{csv_path.name}':")
    for col, amp in amplitudes.items():
        print(f"  {col}  →  amplitude {amp:.4f} W")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Processa CSV GREEND selecionando a coluna de maior amplitude como mains."
    )
    parser.add_argument("csv", type=Path, help="Caminho do arquivo CSV")
    parser.add_argument("--prefix", type=str, default="", help="Prefixo para os arquivos de saída (ex: 01)")
    parser.add_argument("--list-columns", action="store_true", help="Lista colunas e amplitudes, sem processar")
    args = parser.parse_args()

    csv_path = args.csv.resolve()
    if not csv_path.exists():
        print(f"Erro: arquivo não encontrado — {csv_path}")
        sys.exit(1)

    if args.list_columns:
        list_columns(csv_path)
        sys.exit(0)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    stem = csv_path.stem
    original_name = f"{args.prefix}_{stem}" if args.prefix else stem

    print(f"\n📂 Arquivo: {csv_path.name}" + (f"  (prefixo: {args.prefix})" if args.prefix else ""))

    print("⏳ Carregando e selecionando coluna de maior amplitude...")
    series, mains_col = load_and_prepare(csv_path)
    print(f"\n   Coluna selecionada: {mains_col}")
    print(f"   Intervalo: {series.index[0]}  →  {series.index[-1]}")
    print(f"   Total de minutos após resample: {len(series)}")

    first_midnight = find_first_midnight(series)
    if first_midnight is None:
        print("❌ Nenhuma meia-noite (00:00:00) encontrada nos dados.")
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