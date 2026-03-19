import os
import json
from datetime import datetime, timezone, timedelta
import plotext as plt
import matplotlib.pyplot as plt_img

pasta = "output"
pasta_view = "view"
intervalo = 60  # 1 minuto

# criar pasta view se não existir
os.makedirs(pasta_view, exist_ok=True)

utc_minus_3 = timezone(timedelta(hours=-3))

series = {}

def extrair_info(arquivo):
    nome, data1, data2 = arquivo.replace(".json", "").split("--")
    return nome, data1, data2

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

    nome, data1, data2 = extrair_info(arquivo)

    data_base = datetime.strptime(data2, "%Y-%m-%d")
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

    series[nome][data2] = {
        "serie": serie_arquivo,
        "arquivo": arquivo  # guardar nome original
    }

    print(f"{arquivo} -> {len(serie_arquivo)} pontos")

# =========================
# 2. Menu interativo
# =========================

while True:
    prefixos = list(series.keys())

    print("\nPrefixos disponíveis:")
    for i, p in enumerate(prefixos):
        print(f"{i} -> {p}")

    try:
        idx_prefixo = int(input("\nEscolha o prefixo (ou -1 para sair): "))
        if idx_prefixo == -1:
            break

        prefixo_escolhido = prefixos[idx_prefixo]
    except:
        print("Entrada inválida.")
        continue

    dias = sorted(series[prefixo_escolhido].keys())

    print(f"\nDias disponíveis para {prefixo_escolhido}:")
    for i, d in enumerate(dias):
        print(f"{i} -> {d}")

    try:
        idx_dia = int(input("\nEscolha o dia: "))
        dia_escolhido = dias[idx_dia]
    except:
        print("Entrada inválida.")
        continue

    info = series[prefixo_escolhido][dia_escolhido]
    serie = info["serie"]
    nome_arquivo = info["arquivo"]

    potencias = [p for _, p in serie]

    # =========================
    # 3. Plot no terminal
    # =========================
    plt.clear_data()
    plt.clear_figure()

    plt.plot(potencias)

    plt.title(f"{prefixo_escolhido} - {dia_escolhido}")
    plt.xlabel("Tempo (min)")
    plt.ylabel("Potência")

    plt.show()

    # =========================
    # 4. Perguntar se quer salvar
    # =========================
    salvar = input("\nDeseja salvar como PNG? (s/n): ").lower()

    if salvar == "s":
        nome_png = nome_arquivo.replace(".json", ".png")
        caminho_png = os.path.join(pasta_view, nome_png)

        plt_img.figure()
        plt_img.plot(potencias)

        plt_img.title(f"{prefixo_escolhido} - {dia_escolhido}")
        plt_img.xlabel("Tempo (min)")
        plt_img.ylabel("Potência")

        plt_img.savefig(caminho_png)
        plt_img.close()

        print(f"Salvo em: {caminho_png}")

    input("\nPressione Enter para continuar...")