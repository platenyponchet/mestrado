import os
import json
import numpy as np
import pandas as pd
from scipy.stats import entropy as scipy_entropy

input_path = "output"

files = [f for f in os.listdir(input_path) if f.endswith(".json")]

def calcular_features(serie):
    x = np.array(serie)
    
    # --- Estatísticas básicas ---
    mean = np.mean(x)
    median = np.median(x)
    max_val = np.max(x)
    min_val = np.min(x)
    
    # --- Variabilidade ---
    std = np.std(x)
    cv = std / mean if mean != 0 else 0
    
    # --- Dinâmica ---
    diff = np.diff(x)
    mean_abs_diff = np.mean(np.abs(diff))
    std_diff = np.std(diff)
    max_diff = np.max(np.abs(diff))
    
    # --- Picos ---
    threshold = mean + 2 * std
    peaks = x > threshold
    peak_count = np.sum(peaks)
    peak_ratio = peak_count / len(x)
    
    # --- Autocorrelação ---
    def autocorr(x, lag):
        if len(x) <= lag:
            return 0
        return np.corrcoef(x[:-lag], x[lag:])[0, 1]
    
    autocorr_lag1 = autocorr(x, 1)
    autocorr_lag60 = autocorr(x, 60)
    
    # --- Entropia ---
    hist, _ = np.histogram(x, bins=50, density=True)
    hist = hist + 1e-12
    ent = scipy_entropy(hist)
    
    return [
        mean, median, max_val, min_val,
        std, cv,
        mean_abs_diff, std_diff, max_diff,
        peak_count, peak_ratio,
        autocorr_lag1, autocorr_lag60,
        ent
    ]

# 🔥 Criar matriz
X = []
nomes = []

for file in files:
    file_path = os.path.join(input_path, file)
    
    try:
        with open(file_path, "r") as f:
            serie = json.load(f)
        
        features = calcular_features(serie)
        
        X.append(features)
        nomes.append(file)
    
    except Exception as e:
        print(f"{file}: erro -> {e}")

# Converter para numpy
X = np.array(X)

print("Shape da matriz:", X.shape)

# 🔥 Salvar como CSV (mais fácil de visualizar)
colunas = [
    "mean", "median", "max", "min",
    "std", "cv",
    "mean_abs_diff", "std_diff", "max_diff",
    "peak_count", "peak_ratio",
    "autocorr_lag1", "autocorr_lag60",
    "entropy"
]

df = pd.DataFrame(X, columns=colunas)
df.insert(0, "arquivo", nomes)

df.to_csv("features.csv", index=False)

print("Arquivo features.csv salvo com sucesso!")