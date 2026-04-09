"""
process_energy_csv3.py
----------------------
Lê um CSV sem header onde cada linha representa um segundo consecutivo.
A primeira coluna é o valor de mains. Reamostra para 1 minuto (média de
60 segundos), encontra a primeira meia-noite e gera até 7 arquivos JSON
com os dias completos.

Uso:
    python process_energy_csv3.py <caminho_do_csv> [--prefix PREFIXO] [--start "YYYY-MM-DD HH:MM:SS"]

    --start define o timestamp do primeiro registro (padrão: 1970-01-01 00:00:00 UTC).
    Passe a data/hora real de início dos dados para que a meia-noite seja detectada corretamente.
"""

import sys
import json
import pandas as pd
from pathlib import Path


def load_and_prepare(csv_path: Path, start_time: pd.Timestamp) -> pd.Series:
    """Lê o CSV, constrói índice temporal de 1s e reamostra para 1 min."""
    df = pd.read_csv(csv_path, header=None)

    # Apenas a primeira coluna interessa
    mains = df.iloc[:, 0]

    # Constrói índice de segundos a partir do instante inicial fornecido
    index = pd.date_range(start=start_time, periods=len(mains), freq="1s")
    series_sec = pd.Series(mains.values, index=index, dtype=float, name="mains")

    # Reamostra para 1 minuto usando a média dos 60 valores
    series_min = series_sec.resample("1min").mean()

    return series_min


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

        if len(day_data) == 1440 and not day_data.isna().any():
            values = [round(float(v), 4) for v in day_data]
            complete_days.append((current, values))
        else:
            missing = day_data.isna().sum()
            if missing > 0:
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


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Processa CSV de energia (sem header, 1 linha/segundo) e gera JSONs diários."
    )
    parser.add_argument("csv", type=Path, help="Caminho do arquivo CSV")
    parser.add_argument("--prefix", type=str, default="", help="Prefixo para os arquivos de saída (ex: 01)")
    parser.add_argument(
        "--start",
        type=str,
        default=None,
        help='Timestamp do primeiro registro, ex: "2016-02-08 18:30:00". '
             'Se omitido, usa 1970-01-01 00:00:00 UTC (apenas para testes).',
    )
    args = parser.parse_args()

    csv_path = args.csv.resolve()
    if not csv_path.exists():
        print(f"Erro: arquivo não encontrado — {csv_path}")
        sys.exit(1)

    if args.start:
        start_time = pd.Timestamp(args.start, tz="UTC")
    else:
        print("⚠️  --start não informado. Usando 1970-01-01 00:00:00 UTC como referência.")
        start_time = pd.Timestamp("1970-01-01 00:00:00", tz="UTC")

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    stem = csv_path.stem
    original_name = f"{args.prefix}_{stem}" if args.prefix else stem

    print(f"\n📂 Arquivo: {csv_path.name}" + (f"  (prefixo: {args.prefix})" if args.prefix else ""))
    print(f"   Início assumido: {start_time}")

    print("⏳ Carregando e reamostrando dados...")
    series = load_and_prepare(csv_path, start_time)
    print(f"   Intervalo: {series.index[0]}  →  {series.index[-1]}")
    print(f"   Total de minutos após resample: {len(series)}")

    first_midnight = find_first_midnight(series)
    if first_midnight is None:
        print("❌ Nenhuma meia-noite (00:00:00) encontrada nos dados.")
        print("   Verifique se --start está correto.")
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