"""
process_energy_csv.py
---------------------
Lê um CSV com colunas 'unix_ts' e 'mains', reamostra para 1 minuto,
encontra a primeira meia-noite e gera até 7 arquivos JSON com os dias completos.

Uso:
    python process_energy_csv.py <caminho_do_csv>
"""

import sys
import json
import math
import pandas as pd
from pathlib import Path


def load_and_prepare(csv_path: Path) -> pd.DataFrame:
    """Lê o CSV, converte timestamp, ordena e reamostra para 1 min."""
    df = pd.read_csv(csv_path, usecols=["unix_ts", "mains"])

    df["datetime"] = pd.to_datetime(df["unix_ts"], unit="s", utc=True)
    df = df.drop(columns=["unix_ts"])

    df = df.sort_values("datetime").set_index("datetime")

    # Reamostra para frequência de 1 minuto usando a média
    df_resampled = df["mains"].resample("1min").mean()

    return df_resampled


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
    A partir de 'start', percorre dia a dia e coleta os dias com 1440 valores.
    Retorna lista de (data_do_dia, lista_de_valores).
    """
    complete_days = []
    current = start

    while len(complete_days) < max_days:
        day_end = current + pd.Timedelta(days=1)
        day_data = series[(series.index >= current) & (series.index < day_end)]

        if len(day_data) == 1440:
            # Substitui NaN por None para serialização JSON limpa
            values = [None if math.isnan(v) else round(float(v), 4) for v in day_data]
            complete_days.append((current, values))

        current = day_end

        # Para se não houver mais dados
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


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Processa CSV de energia e gera JSONs diários.")
    parser.add_argument("csv", type=Path, help="Caminho do arquivo CSV")
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

    # 1-4. Carregar, converter, ordenar e reamostrar
    print("⏳ Carregando e reamostrando dados...")
    series = load_and_prepare(csv_path)
    print(f"   Intervalo: {series.index[0]}  →  {series.index[-1]}")
    print(f"   Total de minutos após resample: {len(series)}")

    # 5. Primeira meia-noite
    first_midnight = find_first_midnight(series)
    if first_midnight is None:
        print("❌ Nenhuma meia-noite (00:00:00) encontrada nos dados.")
        sys.exit(1)
    print(f"🕛 Primeira meia-noite: {first_midnight}")

    # 6-7. Dias completos
    print("🔍 Procurando dias completos (1440 min)...")
    complete_days = extract_complete_days(series, first_midnight, max_days=7)

    if not complete_days:
        print("⚠️  Nenhum dia completo encontrado.")
        sys.exit(0)

    print(f"✅ {len(complete_days)} dia(s) completo(s) encontrado(s).\n")

    # 8-9. Salvar JSONs
    save_json_files(complete_days, original_name, first_midnight, output_dir)

    print(f"\n🎉 Concluído! Arquivos salvos em: {output_dir}")


if __name__ == "__main__":
    main()