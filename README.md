# Benchmark de Compressores de Séries Temporais

Framework para avaliação e comparação de algoritmos de compressão aplicados a séries temporais de consumo de energia elétrica. Desenvolvido como parte de dissertação de mestrado.

---

## Sumário

- [Visão Geral](#visão-geral)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Algoritmos de Compressão](#algoritmos-de-compressão)
- [Métricas de Qualidade](#métricas-de-qualidade)
- [Datasets](#datasets)
- [Scripts Principais](#scripts-principais)
- [Scripts Auxiliares](#scripts-auxiliares)
- [Dependências](#dependências)
- [Fluxo de Trabalho](#fluxo-de-trabalho)

---

## Visão Geral

O projeto compara cinco algoritmos de compressão aplicados a séries temporais de medidores inteligentes (smart meters). Cada série representa o consumo de potência elétrica de uma instalação ao longo de um dia, com leituras a cada 1 minuto (1.440 pontos por dia).

O objetivo é avaliar o trade-off entre taxa de compressão, qualidade da reconstrução, tempo de execução e uso de memória.

---

## Estrutura do Projeto

```
mestrado/
├── main.py                  # Compressão interativa de uma série
├── experiment.py            # Benchmark em lote sobre todos os datasets
├── resume.py                # Validação de dados brutos (dias completos)
├── generate_samples.py      # Conversão de CSV bruto para JSON
├── features.py              # Extração de features estatísticas
├── clustering.py            # Clusterização K-means dos datasets
├── view.py                  # Visualização interativa de séries
│
├── src/
│   └── compressors/
│       ├── wavelet/         # Transformada Wavelet Discreta
│       ├── dct/             # Transformada Discreta do Cosseno
│       ├── sdt/             # Segmented Data Transform
│       ├── rdp/             # Ramer-Douglas-Peucker
│       ├── arcsdt/          # ARC-SDT (SDT com controle PID adaptativo)
│       └── utils/
│           ├── metrics.py   # Cálculo de métricas de qualidade
│           └── monitor.py   # Monitoramento de tempo e memória
│
├── public/
│   ├── datasets/            # 167 arquivos JSON (datasets públicos)
│   └── src/                 # Scripts de aquisição dos datasets públicos
│
├── private/
│   └── datasets/            # 89 arquivos JSON (dados locais brasileiros)
│
├── analysis/
│   └── src/
│       ├── joint.py         # Visualização comparativa pós-experimento
│       └── sql.py
│
├── data/                    # CSVs brutos de entrada
├── output/                  # JSONs gerados por generate_samples.py
├── experiments/             # resultados.csv gerado por experiment.py
├── compressions/            # PNGs gerados por main.py
└── views/                   # PNGs gerados por view.py
```

---

## Algoritmos de Compressão

Todos os compressores estão em `src/compressors/` e seguem a mesma interface: recebem uma série `[(timestamp, valor), ...]` e retornam a série reconstruída, além de expor os atributos `compression_ratio`, `execution_time`, `memory_usage_mb` e `metrics`.

### Wavelet (`wavelet/`)

Compressão por decomposição wavelet com limiarização (*hard thresholding*).

**Como funciona:**
1. Normaliza a série para `[0, 1]`
2. Aplica decomposição wavelet em N níveis (`pywt`)
3. Mantém apenas os K maiores coeficientes (descarta os demais — zerando-os)
4. Reconstrói via transformada wavelet inversa

**Parâmetros:**
| Parâmetro | Descrição | Padrão |
|-----------|-----------|--------|
| `wavelet` | Família wavelet (`db4`, `bior4.4`, `sym4`, `haar`) | `db4` |
| `level`   | Número de níveis de decomposição | `4` |
| `cr`      | Percentual de coeficientes a remover (%) | — |

---

### DCT (`dct/`)

Compressão no domínio da frequência via Transformada Discreta do Cosseno.

**Como funciona:**
1. Normaliza a série
2. Aplica DCT ortogonal
3. Mantém apenas os K primeiros coeficientes (baixas frequências)
4. Aplica DCT inversa para reconstrução

**Parâmetros:**
| Parâmetro | Descrição |
|-----------|-----------|
| `cr` | Percentual de coeficientes a remover (%) |

---

### SDT (`sdt/`)

Compressão por corredor de erro (*Segmented Data Transform* / método do corredor).

**Como funciona:**
1. Parte do primeiro ponto e define um corredor de erro `±error` ao redor da trajetória
2. Calcula restrições de inclinação para manter novos pontos dentro do corredor
3. Quando um ponto viola as restrições, salva o ponto limite e reinicia o corredor
4. A reconstrução é feita por interpolação linear entre os pontos salvos

**Parâmetros:**
| Parâmetro | Descrição |
|-----------|-----------|
| `error` | Desvio vertical máximo permitido |

> Em `experiment.py`, o SDT usa **busca binária** sobre `error` para atingir um `target_cr` alvo.

---

### RDP (`rdp/`)

Simplificação geométrica de curvas via algoritmo Ramer-Douglas-Peucker.

**Como funciona:**
1. Recursivamente encontra o ponto com maior distância perpendicular à reta
2. Se a distância for maior que `epsilon`, divide a curva e repete nos sub-segmentos
3. Caso contrário, descarta os pontos intermediários
4. A reconstrução é feita por interpolação linear entre os pontos mantidos

**Parâmetros:**
| Parâmetro | Descrição |
|-----------|-----------|
| `epsilon` | Distância perpendicular máxima tolerada |

> Em `experiment.py`, o RDP também usa busca binária sobre `epsilon`.

---

### ARC-SDT (`arcsdt/`)

Extensão do SDT com controlador PID para ajuste dinâmico da taxa de compressão.

**Como funciona:**
1. Executa o SDT com um erro inicial baseado em `percentual_error` × RMS da série
2. A cada `update_interval` pontos, mede a taxa de compressão atual
3. O controlador PID calcula o ajuste: `Δerror = Kp·e + Ki·∫e + Kd·Δe`, onde `e = target_cr - current_cr`
4. Atualiza o erro do corredor para convergir ao `target_cr`

**Parâmetros:**
| Parâmetro | Descrição | Padrão |
|-----------|-----------|--------|
| `percentual_error` | Erro inicial como % do RMS | `10.0` |
| `target_cr` | Taxa de compressão alvo (%) | `80.0` |
| `kp` | Ganho proporcional do PID | `10.0` |
| `ki` | Ganho integral do PID | `2.0` |
| `kd` | Ganho derivativo do PID | `0.0` |
| `update_interval` | Intervalo de atualização (pontos) | `1` |
| `min_absolute_error` | Piso para o erro absoluto | `0.001` |

---

## Métricas de Qualidade

Calculadas em `src/compressors/utils/metrics.py` após cada compressão:

| Métrica | Descrição |
|---------|-----------|
| **MSE** | Erro quadrático médio |
| **RMSE** | Raiz do erro quadrático médio |
| **NRMSE** | RMSE normalizado pelo range da série |
| **MAPE** | Erro percentual absoluto médio |
| **ISD** | Distância integral ao quadrado |
| **PRD** | Percent Root-mean-square Difference |
| **SNR** | Relação sinal-ruído |
| **PSNR** | SNR de pico |
| **SSIM** | Índice de similaridade estrutural |
| **EnergyError** | Erro relativo na energia total |
| **EnergyErrorTotal** | Erro absoluto na energia total |
| **PeakRecall** | Fração dos picos originais recuperados |
| **PeakAmplitudeError** | Erro médio na amplitude dos picos |

O monitoramento de tempo e memória (`utils/monitor.py`) usa uma thread paralela com `psutil` para capturar o pico de uso de RAM durante a compressão.

---

## Datasets

### Formato

Cada arquivo segue o padrão de nome:

```
[Nome]--[DataInicioArquivoBase]--[DataInicioDiaRecortado].json
```

O conteúdo é um array JSON de floats representando a potência em Watts, com uma leitura por minuto:

```json
[123.4, 125.0, 118.7, ...]   // 1.440 valores = 1 dia completo
```

### Datasets Públicos (`public/datasets/` — 167 arquivos)

Obtidos de fontes acadêmicas por meio dos scripts em `public/src/`:

| Script | Fonte |
|--------|-------|
| `01_rae.py` | RAE (empresa elétrica espanhola) |
| `03_ecodata.py` | EcoData (consumo residencial) |
| `04_greend.py` | GreenD (medidores inteligentes) |
| `05_indian.py` | Indian Smart Meter |
| Outros | COMBED, Dryad, IDEAL, UKDALE, Smart* |

### Datasets Privados (`private/datasets/` — 89 arquivos)

Dados de instalações brasileiras identificadas por nome (ex.: AlfredoVolpi, Andrey, CentroCultural, ISEA, LSD, PDC, etc.).

---

## Scripts Principais

### `main.py` — Compressão Interativa

Permite explorar uma única série com um compressor de forma interativa.

```bash
python3 main.py
```

**Fluxo:**
1. Escolha a pasta de dados (pública ou privada)
2. Selecione o prefixo (nome do dispositivo/local)
3. Selecione o dia
4. Informe quantos pontos usar (máx. 1.440)
5. Escolha o algoritmo e configure seus parâmetros
6. Veja os resultados no terminal e opcionalmente visualize o gráfico
7. Salve o gráfico comparativo em PNG (`compressions/`)

---

### `experiment.py` — Benchmark em Lote

Executa todas as combinações de algoritmos, janelas e taxas de compressão sobre todos os datasets. Salva os resultados de forma incremental em `experiments/resultados.csv`.

```bash
python3 experiment.py               # Execução completa
python3 experiment.py --test        # Validação rápida (CR=80, janela=720)
python3 experiment.py --volpi       # Modo ARC-SDT sobre AlfredoVolpi
```

**Combinações padrão:**
- **Algoritmos:** Wavelet-db4, Wavelet-bior4.4, Wavelet-sym4, DCT, ARC-SDT, SDT, RDP
- **Taxas de compressão alvo:** 10%, 20%, ..., 90%
- **Tamanhos de janela:** 15, 60, 360, 720, 1.440 pontos

**Colunas do CSV de saída:**

```
arquivo, data, metodo, algoritmo, target_cr, janela,
compression_ratio, execution_time, memory_usage_mb,
MSE, RMSE, NRMSE, MAPE, ISD, PRD, SNR, PSNR, SSIM,
EnergyError, EnergyErrorTotal, PeakRecall, PeakAmplitudeError
```

---

## Scripts Auxiliares

### `resume.py` — Validação de Dados Brutos

Verifica os arquivos CSV em `data/` e reporta quais dias têm registros completos (1.440 leituras).

```bash
python3 resume.py
```

---

### `generate_samples.py` — Geração de Amostras

Converte arquivos CSV brutos para o formato JSON padrão, extraindo apenas os dias com dados completos.

```bash
python3 generate_samples.py
```

Saída: arquivos JSON em `output/`.

---

### `features.py` — Extração de Features

Extrai 14 features estatísticas de cada série temporal:

| Feature | Descrição |
|---------|-----------|
| mean, median, min, max | Estatísticas básicas |
| std, cv | Desvio padrão e coeficiente de variação |
| mean_diff, std_diff, max_diff | Derivadas (diferenças consecutivas) |
| peak_count, peak_ratio | Contagem e razão de picos |
| autocorr_lag1, autocorr_lag60 | Autocorrelação em lag 1 e 60 min |
| entropy | Entropia da distribuição de valores |

```bash
python3 features.py
```

Saída: `features.csv`.

---

### `clustering.py` — Clusterização

Agrupa os datasets em clusters via K-means sobre as features extraídas. Determina o K ideal pelo método do cotovelo (*elbow*) e silhouette score.

```bash
python3 clustering.py
```

Saídas: `features_clustered.csv`, `elbow.png`, `silhouette.png`.

---

### `view.py` — Visualização de Séries

Exibe séries temporais no terminal e permite salvar gráficos PNG em `views/`.

```bash
python3 view.py
```

---

### `analysis/src/joint.py` — Análise Comparativa

Gera gráficos JointGrid comparando dois algoritmos a partir do `resultados.csv`.

```bash
python3 analysis/src/joint.py \
  --dataset experiments/resultados.csv \
  --algoritmo dct \
  --target_cr 80 \
  --janela 720
```

---

## Dependências

O projeto usa um ambiente virtual local (`venv/`). Principais bibliotecas:

| Biblioteca | Uso |
|------------|-----|
| `numpy`, `scipy` | Computação numérica, DCT |
| `pywt` | Transformadas wavelet |
| `scikit-image` | Métrica SSIM |
| `scikit-learn` | K-means |
| `pandas` | Manipulação de dados tabulares |
| `psutil` | Monitoramento de memória |
| `matplotlib` | Geração de gráficos PNG |
| `plotext` | Visualização no terminal |
| `seaborn` | Gráficos estatísticos |

---

## Fluxo de Trabalho

```
1. AQUISIÇÃO DE DADOS
   CSV bruto (data/)
     └─ resume.py           → validar dias completos
     └─ generate_samples.py → output/*.json

   Datasets públicos
     └─ public/src/*.py     → public/datasets/*.json

2. ANÁLISE EXPLORATÓRIA
   features.py              → features.csv
   clustering.py            → features_clustered.csv
   view.py                  → visualizar séries

3. EXPERIMENTOS
   main.py                  → compressão interativa (uma série)
   experiment.py            → benchmark completo → experiments/resultados.csv

4. ANÁLISE DOS RESULTADOS
   analysis/src/joint.py    → gráficos comparativos
```
