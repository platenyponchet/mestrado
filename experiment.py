#! /usr/bin/env python3

import os
import json
import csv
import sys
from datetime import datetime, timezone, timedelta

from src.compressors.wavelet import WaveletCompressor
from src.compressors.sdt import SDTCompressor
from src.compressors.dct import DCTCompressor
from src.compressors.rdp import RDPCompressor
from src.compressors.arcsdt import ARCSDTCompressor

import argparse

pasta = "output"
intervalo = 60
utc_minus_3 = timezone(timedelta(hours=-3))

parser = argparse.ArgumentParser()
parser.add_argument("--test", action="store_true", help="Roda apenas janela=1440 e target_cr=80 para validação")
parser.add_argument("--volpi", action="store_true", help="Roda apenas AlfredoVolpi com arcsdt e janela 720, mostrando cada compressão")
args = parser.parse_args()

TARGET_CRS = [80] if (args.test or args.volpi) else list(range(10, 91, 10))
JANELAS = [720] if (args.test or args.volpi) else [360]

FILTER_NOME  = ["AlfredoVolpi"] if args.volpi else None
FILTER_ALGOS = [("arcsdt", "arcsdt")] if args.volpi else None

# =========================
# Display
# =========================
def clear_line(n=1):
    for _ in range(n):
        sys.stdout.write("\033[F\033[K")
    sys.stdout.flush()

def print_progress(executados, total, nome, data, metodo, target_cr, janela, cr_real, status, log_lines):
    pct = 100 * executados / total if total else 0
    bar_len = 40
    filled = int(bar_len * pct / 100)
    bar = "█" * filled + "░" * (bar_len - filled)

    while len(log_lines) > 6:
        log_lines.pop(0)

    lines = [
        "",
        f"  Benchmark de Compressores",
        f"  ─────────────────────────────────────────────────",
        f"  Progresso : [{bar}] {pct:5.1f}%",
        f"  Série     : {nome} - {data}",
        f"  Método    : {metodo:<35} target: {target_cr:.1f}%",
        f"  Janela    : {janela} pts      CR real: {cr_real:.1f}%   status: {status}",
        f"  ─────────────────────────────────────────────────",
        f"  Log recente:",
    ] + [f"    {l}" for l in log_lines] + [""]

    if print_progress._last_lines > 0:
        clear_line(print_progress._last_lines)

    for line in lines:
        print(line)

    print_progress._last_lines = len(lines)
    sys.stdout.flush()

print_progress._last_lines = 0

# =========================
# Helpers
# =========================
def extrair_info(arquivo):
    nome, data1, data2 = arquivo.replace(".json", "").split("--")
    return nome, data2

def extrair_data(arquivo):
    data_str = arquivo.replace(".json", "").split("--")[2]
    return datetime.strptime(data_str, "%Y-%m-%d")

def media_metrics(lista_metrics):
    if not lista_metrics:
        return {}
    keys = lista_metrics[0].keys()
    result = {}
    for k in keys:
        vals = [m[k] for m in lista_metrics if m.get(k) is not None]
        result[k] = sum(vals) / len(vals) if vals else None
    return result

# =========================
# Busca binária
# =========================
def fit_sdt(serie, target_cr, tolerancia=2.0, max_iter=30):
    lo, hi = 0.1, 1e7
    best = None
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        c = SDTCompressor(error=mid)
        c.compress(serie)
        best = c
        if abs(c.compression_ratio - target_cr) <= tolerancia:
            break
        if c.compression_ratio < target_cr:
            lo = mid
        else:
            hi = mid
    return best

def fit_rdp(serie, target_cr, tolerancia=2.0, max_iter=30):
    lo, hi = 0.1, 1e7
    best = None
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        c = RDPCompressor(epsilon=mid)
        c.compress(serie)
        best = c
        if abs(c.compression_ratio - target_cr) <= tolerancia:
            break
        if c.compression_ratio < target_cr:
            lo = mid
        else:
            hi = mid
    return best

def rodar_compressor(algo, serie, target_cr):
    if algo == "wavelet":
        c = WaveletCompressor(cr=target_cr)
        c.compress(serie)
    elif algo == "dct":
        c = DCTCompressor(cr=target_cr)
        c.compress(serie)
    elif algo == "arcsdt":
        c = ARCSDTCompressor(target_cr=target_cr)
        c.compress(serie)
    elif algo == "sdt":
        c = fit_sdt(serie, target_cr)
    elif algo == "rdp":
        c = fit_rdp(serie, target_cr)
    return c

# =========================
# 1. Carregar dados
# =========================
print("\n  Carregando arquivos...")

series = {}
arquivos = sorted(
    [a for a in os.listdir(pasta) if a.endswith(".json")],
    key=extrair_data
)

for arquivo in arquivos:
    caminho = os.path.join(pasta, arquivo)
    nome, data = extrair_info(arquivo)
    data_base = datetime.strptime(data, "%Y-%m-%d").replace(tzinfo=utc_minus_3)

    with open(caminho, "r", encoding="utf-8") as f:
        potencias = json.load(f)

    serie_arquivo = [
        ((data_base + timedelta(seconds=i * intervalo)).timestamp(), p)
        for i, p in enumerate(potencias)
    ]

    if nome not in series:
        series[nome] = {}
    series[nome][data] = serie_arquivo

print(f"  {len(arquivos)} arquivos carregados.\n")

# =========================
# 2. Experimentos
# =========================
resultados = []
log_lines = []
erros_finais = []

# ALGOS = [
#     ("wavelet", "wavelet-db4"),
#     ("dct",     "dct"),
#     ("arcsdt",  "arcsdt"),
#     ("sdt",     "sdt"),
#     ("rdp",     "rdp"),
# ]
ALGOS = [
    ("wavelet", "wavelet-db4"),
    ("arcsdt",  "arcsdt"),
]

algos_ativos = FILTER_ALGOS if FILTER_ALGOS else ALGOS

# Preparar CSV
os.makedirs("experiments", exist_ok=True)
caminho_csv = "experiments/resultados.csv"

# LIMPA O ARQUIVO NO INÍCIO DA EXECUÇÃO
if os.path.exists(caminho_csv):
    os.remove(caminho_csv)

csv_header_escrito = False

total_series = sum(
    1 for nome in series
    for _ in series[nome]
    if FILTER_NOME is None or nome in FILTER_NOME
)
total = total_series * len(TARGET_CRS) * len(JANELAS) * len(algos_ativos)
executados = 0

for nome, dias in series.items():
    if FILTER_NOME and nome not in FILTER_NOME:
        continue
    for data, serie in dias.items():
        for target_cr in TARGET_CRS:
            for janela in JANELAS:
                for algo, label in algos_ativos:
                    executados += 1
                    metodo = f"{label}-red{target_cr}-w{janela}"

                    if not args.volpi:
                        print_progress(executados, total, nome, data, metodo, target_cr, janela, 0.0, "rodando...", log_lines)

                    janelas = [serie[i:i+janela] for i in range(0, len(serie), janela)]
                    janelas = [j for j in janelas if len(j) == janela]

                    crs = []
                    tempos = []
                    memorias = []
                    lista_metrics = []

                    try:
                        for idx, j in enumerate(janelas):
                            c = rodar_compressor(algo, j, target_cr)
                            crs.append(c.compression_ratio)
                            tempos.append(c.execution_time)
                            memorias.append(c.memory_usage_mb)
                            if c.metrics:
                                lista_metrics.append(c.metrics)
                    except Exception as e:
                        erros_finais.append(f"Erro em {metodo} ({nome}): {str(e)}")
                        continue

                    if not crs: 
                        continue

                    cr_medio = sum(crs) / len(crs)
                    tempo_total = sum(tempos)
                    memoria_media = sum(memorias) / len(memorias)
                    metrics_medias = media_metrics(lista_metrics)

                    row = {
                        "arquivo": nome,
                        "data": data,
                        "metodo": metodo,
                        "algoritmo": label,
                        "target_cr": target_cr,
                        "janela": janela,
                        "compression_ratio": cr_medio,
                        "execution_time": tempo_total,
                        "memory_usage_mb": memoria_media,
                    }
                    row.update(metrics_medias)
                    
                    # ESCRITA INCREMENTAL
                    with open(caminho_csv, "a", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
                        if not csv_header_escrito:
                            writer.writeheader()
                            csv_header_escrito = True
                        writer.writerow(row)

                    if not args.volpi:
                        log_lines.append(f"✓ {metodo:<45} CR: {cr_medio:.1f}%")
                        print_progress(executados, total, nome, data, metodo, target_cr, janela, cr_medio, "ok", log_lines)

# =========================
# 3. Finalização
# =========================
if erros_finais:
    print("\n  ⚠️  Erros durante a execução:")
    for e in erros_finais: 
        print(f"    - {e}")

print(f"\n  ✓ Concluído! Resultados em: {caminho_csv}\n")