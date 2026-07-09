#! /usr/bin/env python3
"""
Experimento dedicado e pequeno: compara wavelet-haar em level=3 (configuração
principal deste trabalho) vs level=6 (o dobro), para ilustrar o efeito do
nível de decomposição sobre qualidade e viabilidade em janelas pequenas.
Não faz parte do pipeline principal (experiment.py); roda separado e salva
em experiments/archive/, para uso em uma figura/tabela dedicada na dissertação.
"""

import os
import csv
import json
from datetime import datetime, timezone, timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed

from src.compressors.wavelet import WaveletCompressor

intervalo = 60
utc_minus_3 = timezone(timedelta(hours=-3))

TARGET_CRS = list(range(10, 91, 10))
JANELAS = [15, 60, 360, 720, 1440]
LEVELS = [3, 6]


def extrair_info(arquivo):
    nome, data1, data2 = arquivo.replace(".json", "").split("--")
    return nome, data2


def extrair_data(arquivo):
    data_str = arquivo.replace(".json", "").split("--")[2]
    return datetime.strptime(data_str, "%Y-%m-%d")


def carregar_series(pasta):
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
    return series


def media_metrics(lista_metrics):
    if not lista_metrics:
        return {}
    keys = lista_metrics[0].keys()
    result = {}
    for k in keys:
        vals = [m[k] for m in lista_metrics if m.get(k) is not None]
        result[k] = sum(vals) / len(vals) if vals else None
    return result


def processar_combinacao(tarefa):
    nome, data, serie, target_cr, janela, level = tarefa

    janelas = [serie[i:i+janela] for i in range(0, len(serie), janela)]
    janelas = [j for j in janelas if len(j) == janela]

    crs, tempos, memorias, lista_metrics = [], [], [], []

    try:
        for j in janelas:
            c = WaveletCompressor(cr=target_cr, wavelet="haar", level=level)
            c.compress(j)
            crs.append(c.compression_ratio)
            tempos.append(c.execution_time)
            memorias.append(c.memory_usage_mb)
            if c.metrics:
                lista_metrics.append(c.metrics)
    except Exception as e:
        return {"status": "erro", "erro": f"{nome} {data} level={level}: {e}"}

    if not crs:
        return {"status": "vazio"}

    row = {
        "arquivo": nome,
        "data": data,
        "algoritmo": f"wavelet-haar-lvl{level}",
        "level": level,
        "target_cr": target_cr,
        "janela": janela,
        "compression_ratio": sum(crs) / len(crs),
        "execution_time": sum(tempos),
        "memory_usage_mb": sum(memorias) / len(memorias),
    }
    row.update(media_metrics(lista_metrics))
    return {"status": "ok", "row": row}


def main():
    os.makedirs("experiments/archive", exist_ok=True)

    for sufixo, pasta in [("publico", "public/datasets"), ("privado", "private/datasets")]:
        print(f"\nCarregando {pasta}...")
        series = carregar_series(pasta)

        tarefas = []
        for nome, dias in series.items():
            for data, serie in dias.items():
                for target_cr in TARGET_CRS:
                    for janela in JANELAS:
                        for level in LEVELS:
                            tarefas.append((nome, data, serie, target_cr, janela, level))

        print(f"{len(tarefas)} tarefas ({sufixo}). Rodando com {os.cpu_count()} workers...")

        caminho_csv = f"experiments/archive/comparacao_nivel_haar_{sufixo}.csv"
        header_escrito = False
        erros = []
        ok_count = 0

        with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = [executor.submit(processar_combinacao, t) for t in tarefas]
            for i, future in enumerate(as_completed(futures)):
                resultado = future.result()
                if resultado["status"] == "erro":
                    erros.append(resultado["erro"])
                    continue
                if resultado["status"] == "vazio":
                    continue
                row = resultado["row"]
                with open(caminho_csv, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=list(row.keys()))
                    if not header_escrito:
                        writer.writeheader()
                        header_escrito = True
                    writer.writerow(row)
                ok_count += 1
                if (i + 1) % 500 == 0:
                    print(f"  {i+1}/{len(tarefas)} processadas...")

        print(f"Concluído {sufixo}: {ok_count} linhas salvas em {caminho_csv}")
        if erros:
            print(f"  {len(erros)} erros:")
            for e in erros[:5]:
                print(f"    - {e}")


if __name__ == "__main__":
    main()
