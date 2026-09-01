#! /usr/bin/env python3

import os
import json
import csv
import sys
from datetime import datetime, timezone, timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed

from src.compressors.wavelet import WaveletCompressor
from src.compressors.sdt import SDTCompressor
from src.compressors.dct import DCTCompressor
from src.compressors.rdp import RDPCompressor
from src.compressors.arcsdt import ARCSDTCompressor

import argparse

intervalo = 60
utc_minus_3 = timezone(timedelta(hours=-3))

ALGOS = [
    ("wavelet-haar",    "wavelet-haar"),
    ("wavelet-sym2",    "wavelet-sym2"),
    ("wavelet-bior5.5", "wavelet-bior5.5"),
    ("dct",             "dct"),
    ("arcsdt",          "arcsdt"),
    ("sdt",             "sdt"),
    ("sdt_10",          "sdt_10"),
    ("sdt_25",          "sdt_25"),
    ("sdt_50",          "sdt_50"),
    ("sdt_75",          "sdt_75"),
    ("rdp",             "rdp"),
]

SDT_PARTIAL_FRACS = {"sdt_10": 0.10, "sdt_25": 0.25, "sdt_50": 0.50, "sdt_75": 0.75}

# =========================
# Deletar resultados de uma família específica
# =========================
def menu_deletar_familia():
    resp = input("Deseja deletar resultados de alguma família específica antes de continuar? [s/N]: ").strip().lower()
    if resp != "s":
        return

    opcao_pasta_del = input("Usar pasta (1) pública ou (2) privada? [1]: ").strip()
    sufixo_del = "privado" if opcao_pasta_del == "2" else "publico"
    caminho_csv_del = f"experiments/resultados_{sufixo_del}.csv"

    if not os.path.exists(caminho_csv_del):
        print(f"  Arquivo {caminho_csv_del} não existe. Nada a deletar.\n")
        return

    with open(caminho_csv_del, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    familias = sorted({row.get("algoritmo") for row in rows if row.get("algoritmo")})

    if not familias:
        print("  Nenhuma família encontrada no arquivo de resultados.\n")
        return

    print("\n--- Famílias encontradas em", caminho_csv_del, "---")
    for i, fam in enumerate(familias):
        print(f"  {i} -> {fam}")

    idx_input = input("Escolha a família a deletar (ou Enter para cancelar): ").strip()
    if idx_input == "":
        print("  Cancelado.\n")
        return

    idx_fam = int(idx_input)
    familia_selecionada = familias[idx_fam]

    rows_preservadas = [row for row in rows if row.get("algoritmo") != familia_selecionada]
    n_removidas = len(rows) - len(rows_preservadas)

    with open(caminho_csv_del, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_preservadas)

    print(f"  {n_removidas} linhas de '{familia_selecionada}' removidas de {caminho_csv_del}.\n")

# =========================
# Display
# =========================
def clear_line(n=1):
    for _ in range(n):
        sys.stdout.write("\033[F\033[K")
    sys.stdout.flush()

def print_progress(executados, total, nome, data, metodo, target_cr, janela, cr_real, status, log_lines, n_workers):
    pct = 100 * executados / total if total else 0
    bar_len = 40
    filled = int(bar_len * pct / 100)
    bar = "█" * filled + "░" * (bar_len - filled)

    while len(log_lines) > 6:
        log_lines.pop(0)

    lines = [
        "",
        f"  Benchmark de Compressores ({n_workers} workers)",
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

def fit_sdt_partial(serie, target_cr, frac, tolerancia=2.0, max_iter=30):
    """Calibra a tolerância do SDT por busca binária vendo só os primeiros
    `frac` da janela, depois aplica essa tolerância fixa à janela inteira.
    Simula uma calibração online que não tem acesso ao restante da série."""
    n_calib = max(2, min(len(serie), int(len(serie) * frac)))
    calib_serie = serie[:n_calib]

    lo, hi = 0.1, 1e7
    best_error = None
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        c = SDTCompressor(error=mid)
        c.compress(calib_serie)
        best_error = mid
        if abs(c.compression_ratio - target_cr) <= tolerancia:
            break
        if c.compression_ratio < target_cr:
            lo = mid
        else:
            hi = mid

    c_full = SDTCompressor(error=best_error)
    c_full.compress(serie)
    return c_full

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
    if algo.startswith("wavelet"):
        wavelet = algo.split("-", 1)[1]  # extrai "haar", "sym2" ou "bior5.5"
        c = WaveletCompressor(cr=target_cr, wavelet=wavelet, level=3)
        c.compress(serie)
    elif algo == "dct":
        c = DCTCompressor(cr=target_cr)
        c.compress(serie)
    elif algo == "arcsdt":
        c = ARCSDTCompressor(target_cr=target_cr)
        c.compress(serie)
    elif algo == "sdt":
        c = fit_sdt(serie, target_cr)
    elif algo in SDT_PARTIAL_FRACS:
        c = fit_sdt_partial(serie, target_cr, SDT_PARTIAL_FRACS[algo])
    elif algo == "rdp":
        c = fit_rdp(serie, target_cr)
    return c

# =========================
# Unidade de trabalho (roda em processo worker)
# =========================
def processar_combinacao(tarefa):
    nome, data, serie, target_cr, janela, algo, label, metodo = tarefa

    janelas = [serie[i:i+janela] for i in range(0, len(serie), janela)]
    janelas = [j for j in janelas if len(j) == janela]

    crs = []
    tempos = []
    memorias = []
    lista_metrics = []

    try:
        for j in janelas:
            c = rodar_compressor(algo, j, target_cr)
            crs.append(c.compression_ratio)
            tempos.append(c.execution_time)
            memorias.append(c.memory_usage_mb)
            if c.metrics:
                lista_metrics.append(c.metrics)
    except Exception as e:
        return {"status": "erro", "erro": f"Erro em {metodo} ({nome}): {str(e)}",
                "nome": nome, "data": data, "metodo": metodo, "target_cr": target_cr, "janela": janela}

    if not crs:
        return {"status": "vazio",
                "nome": nome, "data": data, "metodo": metodo, "target_cr": target_cr, "janela": janela}

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

    return {"status": "ok", "row": row,
            "nome": nome, "data": data, "metodo": metodo, "target_cr": target_cr, "janela": janela, "cr_medio": cr_medio}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Roda apenas janela=1440 e target_cr=80 para validação")
    parser.add_argument("--volpi", action="store_true", help="Roda apenas AlfredoVolpi com arcsdt e janela 720, mostrando cada compressão")
    parser.add_argument("--workers", type=int, default=os.cpu_count(), help="Número de processos workers em paralelo (padrão: número de CPUs)")
    args = parser.parse_args()

    n_workers = max(1, args.workers)
    print(f"\n  Usando {n_workers} workers (de {os.cpu_count()} CPUs disponíveis).\n")

    menu_deletar_familia()

    opcao_pasta = input("Usar pasta (1) pública ou (2) privada? [1]: ").strip()
    pasta = "private/datasets" if opcao_pasta == "2" else "public/datasets"

    TARGET_CRS = [80] if (args.test or args.volpi) else list(range(10, 91, 10))
    JANELAS = [720] if (args.test or args.volpi) else [15, 60, 360, 720, 1440]

    FILTER_NOME  = ["AlfredoVolpi"] if args.volpi else None
    FILTER_ALGOS = [("arcsdt", "arcsdt")] if args.volpi else None

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
    log_lines = []
    erros_finais = []

    algos_ativos = FILTER_ALGOS if FILTER_ALGOS else ALGOS

    # Preparar CSV
    os.makedirs("experiments", exist_ok=True)
    sufixo = "privado" if opcao_pasta == "2" else "publico"
    caminho_csv = f"experiments/resultados_{sufixo}.csv"

    familias_existentes = set()
    if os.path.exists(caminho_csv):
        with open(caminho_csv, "r", encoding="utf-8") as f:
            familias_existentes = {row.get("algoritmo") for row in csv.DictReader(f) if row.get("algoritmo")}

    # Menu de modo de execução
    modo_atualizacao = False
    algo_selecionado = None

    if not args.volpi and not args.test:
        print("\n--- Modo de execução ---")
        print("  1 -> Executar todos os algoritmos (substitui CSV existente)")
        print("  2 -> Atualizar resultados de um algoritmo específico")
        modo_input = input("Escolha [1]: ").strip()
        modo = int(modo_input) if modo_input else 1

        if modo == 2:
            print(f"\n--- Selecione o algoritmo a atualizar (já em {caminho_csv} marcados com *) ---")
            for i, (_, label) in enumerate(ALGOS):
                marca = " *" if label in familias_existentes else ""
                print(f"  {i} -> {label}{marca}")
            idx_algo = int(input("Escolha: ").strip())
            algo_selecionado, _ = ALGOS[idx_algo]
            algos_ativos = [ALGOS[idx_algo]]
            modo_atualizacao = True

    csv_header_escrito = False

    if modo_atualizacao and os.path.exists(caminho_csv):
        # Preservar linhas dos outros algoritmos e remover apenas as do selecionado
        rows_preservadas = []
        fieldnames_existentes = None
        with open(caminho_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames_existentes = reader.fieldnames
            for row in reader:
                if row.get("algoritmo") != algo_selecionado:
                    rows_preservadas.append(row)
        with open(caminho_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames_existentes)
            writer.writeheader()
            writer.writerows(rows_preservadas)
        csv_header_escrito = True
        print(f"  {len(rows_preservadas)} linhas preservadas. Recalculando '{algo_selecionado}'...\n")
    else:
        if os.path.exists(caminho_csv):
            os.remove(caminho_csv)

    # =========================
    # Montar lista de tarefas
    # =========================
    tarefas = []
    for nome, dias in series.items():
        if FILTER_NOME and nome not in FILTER_NOME:
            continue
        for data, serie in dias.items():
            for target_cr in TARGET_CRS:
                for janela in JANELAS:
                    for algo, label in algos_ativos:
                        metodo = f"{label}-red{target_cr}-w{janela}"
                        tarefas.append((nome, data, serie, target_cr, janela, algo, label, metodo))

    total = len(tarefas)
    executados = 0
    # Redesenhar a tela só de tempos em tempos: a cada tarefa, o redesenho ANSI no
    # processo principal serializa e vira gargalo, anulando o ganho dos workers em paralelo.
    PRINT_EVERY = max(1, total // 200)

    print(f"  {total} tarefas na fila.\n")

    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        futures = {executor.submit(processar_combinacao, t): t for t in tarefas}

        for future in as_completed(futures):
            executados += 1
            resultado = future.result()

            nome = resultado["nome"]
            data = resultado["data"]
            metodo = resultado["metodo"]
            target_cr = resultado["target_cr"]
            janela = resultado["janela"]

            deve_imprimir = not args.volpi and (executados % PRINT_EVERY == 0 or executados == total)

            if resultado["status"] == "erro":
                erros_finais.append(resultado["erro"])
                if deve_imprimir:
                    print_progress(executados, total, nome, data, metodo, target_cr, janela, 0.0, "erro", log_lines, n_workers)
                continue

            if resultado["status"] == "vazio":
                continue

            row = resultado["row"]
            cr_medio = resultado["cr_medio"]

            # ESCRITA INCREMENTAL (sempre pelo processo principal, sem concorrência)
            with open(caminho_csv, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(row.keys()))
                if not csv_header_escrito:
                    writer.writeheader()
                    csv_header_escrito = True
                writer.writerow(row)

            if deve_imprimir:
                log_lines.append(f"✓ {metodo:<45} CR: {cr_medio:.1f}%")
                print_progress(executados, total, nome, data, metodo, target_cr, janela, cr_medio, "ok", log_lines, n_workers)

    # =========================
    # 3. Finalização
    # =========================
    if erros_finais:
        print("\n  ⚠️  Erros durante a execução:")
        for e in erros_finais:
            print(f"    - {e}")

    print(f"\n  ✓ Concluído! Resultados em: {caminho_csv}\n")


if __name__ == "__main__":
    main()
