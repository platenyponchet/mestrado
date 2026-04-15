# CLAUDE.md — Benchmark de Compressores de Séries Temporais

Dissertação de mestrado. Framework para comparar algoritmos de compressão em séries temporais de consumo elétrico (smart meters). Cada série = 1 dia, 1.440 pontos (1 leitura/minuto), formato JSON de floats.

## Stack

- Python 3.10, ambiente virtual em `venv/`
- `numpy`, `scipy`, `pywt`, `scikit-image`, `scikit-learn`, `pandas`, `psutil`, `matplotlib`, `plotext`, `seaborn`

## Estrutura

```
src/compressors/          # Algoritmos: wavelet/, dct/, sdt/, rdp/, arcsdt/
src/compressors/utils/    # metrics.py, monitor.py
public/datasets/          # 167 JSONs (dados públicos)
private/datasets/         # 89 JSONs (dados brasileiros privados)
experiments/              # resultados.csv (saída do benchmark)
data/                     # CSVs brutos de entrada
output/                   # JSONs gerados por generate_samples.py
```

## Interface dos compressores

Todos seguem a mesma interface:
- **Entrada:** `[(timestamp, valor), ...]`
- **Saída:** série reconstruída
- **Atributos expostos:** `compression_ratio`, `execution_time`, `memory_usage_mb`, `metrics`

## Algoritmos

| Algoritmo | Arquivo | Parâmetro principal |
|-----------|---------|---------------------|
| Wavelet | `wavelet/` | `cr` (% coef. removidos), `wavelet` (db4/bior4.4/sym4/haar), `level` |
| DCT | `dct/` | `cr` |
| SDT | `sdt/` | `error` (desvio vertical máx) — busca binária em experiment.py |
| RDP | `rdp/` | `epsilon` (dist. perpendicular máx) — busca binária em experiment.py |
| ARC-SDT | `arcsdt/` | `target_cr`, `percentual_error`, `kp`, `ki`, `kd`, `update_interval` |

## Comandos

```bash
python3 main.py                          # compressão interativa (1 série)
python3 experiment.py                    # benchmark completo → experiments/resultados_publico.csv ou resultados_privado.csv
python3 experiment.py --test             # validação rápida (CR=80, janela=720)
python3 experiment.py --volpi            # ARC-SDT sobre AlfredoVolpi
python3 features.py                      # extrai features → features.csv
python3 clustering.py                    # K-means → features_clustered.csv
python3 view.py                          # visualiza séries no terminal
python3 resume.py                        # valida dias completos nos CSVs brutos
python3 generate_samples.py              # CSV bruto → JSON (output/)
python3 analysis/src/joint.py --dataset experiments/resultados.csv --algoritmo dct --target_cr 80 --janela 720
```

## Métricas calculadas

MSE, RMSE, NRMSE, MAPE, ISD, PRD, SNR, PSNR, SSIM, EnergyError, EnergyErrorTotal, PeakRecall, PeakAmplitudeError

## Formato do dataset JSON

```json
[123.4, 125.0, 118.7, ...]   // 1.440 floats = 1 dia (Watts, 1/min)
```

Nome do arquivo: `[Nome]--[DataInicioArquivoBase]--[DataInicioDiaRecortado].json`