#! /usr/bin/env python3

import os
import json
from datetime import datetime, timezone, timedelta

import plotext as plt

from src.compressors.wavelet import WaveletCompressor
from src.compressors.sdt import SDTCompressor
from src.compressors.dct import DCTCompressor
from src.compressors.rdp import RDPCompressor
from src.compressors.arcsdt import ARCSDTCompressor

pasta = "public/output"
intervalo = 60  # 1 minuto

utc_minus_3 = timezone(timedelta(hours=-3))

series = {}

# =========================
# Helpers
# =========================
def extrair_info(arquivo):
    nome, data1, data2 = arquivo.replace(".json", "").split("--")
    return nome, data2

def extrair_data(arquivo):
    data_str = arquivo.replace(".json", "").split("--")[2]
    return datetime.strptime(data_str, "%Y-%m-%d")

# =========================
# 1. Carregar dados
# =========================
arquivos = sorted(
    [a for a in os.listdir(pasta) if a.endswith(".json")],
    key=extrair_data
)

for arquivo in arquivos:
    caminho = os.path.join(pasta, arquivo)

    nome, data = extrair_info(arquivo)

    data_base = datetime.strptime(data, "%Y-%m-%d")
    data_base = data_base.replace(tzinfo=utc_minus_3)

    with open(caminho, "r", encoding="utf-8") as f:
        potencias = json.load(f)

    serie_arquivo = []

    for i, potencia in enumerate(potencias):
        dt = data_base + timedelta(seconds=i * intervalo)
        timestamp = dt.timestamp()
        serie_arquivo.append((timestamp, potencia))

    if nome not in series:
        series[nome] = {}

    series[nome][data] = serie_arquivo

    print(f"{arquivo} -> {len(serie_arquivo)} pontos")

# =========================
# 2. Menu
# =========================

prefixos = list(series.keys())

print("\nPrefixos disponíveis:")
for i, p in enumerate(prefixos):
    print(f"{i} -> {p}")

idx_prefixo = int(input("\nEscolha o prefixo: "))
prefixo_escolhido = prefixos[idx_prefixo]

dias = sorted(series[prefixo_escolhido].keys())

print(f"\nDias disponíveis para {prefixo_escolhido}:")
for i, d in enumerate(dias):
    print(f"{i} -> {d}")

idx_dia = int(input("\nEscolha o dia: "))
dia_escolhido = dias[idx_dia]

serie = series[prefixo_escolhido][dia_escolhido]

n_input = input("\nQuantos pontos usar? (máx 1440) [1440]: ")
n_pontos = int(n_input) if n_input.strip() != "" else 1440
serie = serie[:n_pontos]

# =========================
# 3. Escolha do compressor
# =========================

print("\n--- Escolha o compressor ---")
print("1 -> Wavelet")
print("2 -> SDT")
print("3 -> DCT")
print("4 -> RDP")
print("5 -> ARC-SDT")

op = int(input("Escolha: "))

# =========================
# 4. Configuração
# =========================

if op == 1:
    print("\n--- Configuração Wavelet ---")

    print("Wavelets disponíveis:")
    print("  1 -> db4")
    print("  2 -> bior4.4")
    print("  3 -> sym4")
    print("  4 -> haar")
    print("  5 -> outro (digitar manualmente)")

    op_wavelet = int(input("Escolha: "))
    wavelet_map = {1: "db4", 2: "bior4.4", 3: "sym4", 4: "haar"}
    wavelet = wavelet_map.get(op_wavelet) or input("Digite o nome da wavelet: ")

    level_input = input("Nível de decomposição [4]: ")
    level = int(level_input) if level_input.strip() != "" else 4

    cr = float(input("Redução desejada (%) (ex: 90 = remove 90%): "))

    compressor = WaveletCompressor(wavelet=wavelet, level=level, cr=cr)
    nome_metodo = f"wavelet-{wavelet}-lvl{level}-red{cr}"

elif op == 2:
    print("\n--- Configuração SDT ---")

    error = float(input("Erro máximo permitido: "))

    compressor = SDTCompressor(error=error)

    nome_metodo = f"sdt-error{error}"

elif op == 3:
    print("\n--- Configuração DCT ---")

    cr = float(input("Redução desejada (%) (ex: 90 = remove 90%): "))

    compressor = DCTCompressor(cr=cr)

    nome_metodo = f"dct-red{cr}"

elif op == 4:
    print("\n--- Configuração RDP ---")

    epsilon = float(input("Erro máximo (epsilon): "))

    compressor = RDPCompressor(epsilon=epsilon)

    nome_metodo = f"rdp-eps{epsilon}"

elif op == 5:
    print("\n--- Configuração ARC-SDT ---")

    pe_input = input("Erro percentual inicial (%) [10.0]: ")
    percentual_error = float(pe_input) if pe_input.strip() != "" else 10.0

    cr_input = input("Taxa de compressão alvo (%) [90.0]: ")
    target_cr = float(cr_input) if cr_input.strip() != "" else 90.0

    kp_input = input("Kp do PID [10.0]: ")
    kp = float(kp_input) if kp_input.strip() != "" else 10.0

    ki_input = input("Ki do PID [2]: ")
    ki = float(ki_input) if ki_input.strip() != "" else 2.0

    kd_input = input("Kd do PID [0.0]: ")
    kd = float(kd_input) if kd_input.strip() != "" else 0.0

    ui_input = input("Intervalo de atualização do PID [1]: ")
    update_interval = int(ui_input) if ui_input.strip() != "" else 1

    mae_input = input("Erro absoluto mínimo [1.0]: ")
    min_absolute_error = float(mae_input) if mae_input.strip() != "" else 1.0

    compressor = ARCSDTCompressor(
        percentual_error=percentual_error,
        target_cr=target_cr,
        kp=kp,
        ki=ki,
        kd=kd,
        update_interval=update_interval,
        min_absolute_error=min_absolute_error
    )

    nome_metodo = f"arcsdt-tcr{target_cr}-pe{percentual_error}"

else:
    print("Opção inválida")
    exit()

# =========================
# 5. Compressão
# =========================

serie_reconstruida = compressor.compress(serie)

print("\n--- Resultados ---")
print(f"{prefixo_escolhido} - {dia_escolhido}")
print(f"Método: {nome_metodo}")

# =========================
# 6. Visualização
# =========================

visualizar = input("\nDeseja visualizar antes/depois? (s/n): ").lower()

original = [p for _, p in serie]
reconstruido = [p for _, p in serie_reconstruida]

if visualizar == "s":
    plt.clear_data()
    plt.clear_figure()

    plt.plot(original)
    plt.plot(reconstruido)

    plt.title(f"{prefixo_escolhido} - {dia_escolhido} ({nome_metodo})")
    plt.xlabel("Tempo (min)")
    plt.ylabel("Potência")

    plt.show()

# =========================
# 7. Métricas
# =========================

print("\nMétricas:")
print(f"Redução: {compressor.compression_ratio:.2f}%")
print(f"Tempo: {compressor.execution_time:.6f} s")
print(f"Memória: {compressor.memory_usage_mb:.6f} MB")

if compressor.metrics:
    print("\nQualidade da reconstrução:")
    for k, v in compressor.metrics.items():
        if v is None:
            print(f"  {k}: N/A")
        else:
            print(f"  {k}: {v:.6f}")

# =========================
# 8. Salvar PNG
# =========================

salvar_png = input("\nDeseja salvar o gráfico em PNG? (s/n): ").lower()

if salvar_png == "s":
    import matplotlib.pyplot as plt_img

    pasta_saida = "compressions"
    os.makedirs(pasta_saida, exist_ok=True)

    nome_png = f"{prefixo_escolhido}--{dia_escolhido}--{nome_metodo}.png"
    caminho_png = os.path.join(pasta_saida, nome_png)

    plt_img.figure()
    plt_img.plot(original, label="Original")
    plt_img.plot(reconstruido, label="Reconstruído")

    plt_img.title(
        f"{prefixo_escolhido} - {dia_escolhido}\n"
        f"{nome_metodo} | RED={compressor.compression_ratio:.2f}% "
        f"| T={compressor.execution_time:.4f}s "
        f"| RAM={compressor.memory_usage_mb:.4f}MB"
    )

    plt_img.xlabel("Tempo (min)")
    plt_img.ylabel("Potência")

    plt_img.legend()
    plt_img.savefig(caminho_png)
    plt_img.close()

    print(f"PNG salvo em: {caminho_png}")