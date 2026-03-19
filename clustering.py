import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

# =========================
# 1. Carregar dados
# =========================
df = pd.read_csv("features.csv")

nomes = df["arquivo"]
X = df.drop(columns=["arquivo"]).values

# =========================
# 2. Normalização
# =========================
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

print("Dados normalizados!")

# =========================
# 3. Escolha de k (Elbow + Silhouette)
# =========================
inertias = []
silhouettes = []
k_values = range(2, 10)

for k in k_values:
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    
    inertias.append(kmeans.inertia_)
    silhouettes.append(silhouette_score(X_scaled, labels))

# =========================
# 4. Plot Elbow (salvar)
# =========================
plt.figure()
plt.plot(k_values, inertias, marker='o')
plt.title("Elbow Method")
plt.xlabel("k")
plt.ylabel("Inertia")
plt.savefig("elbow.png")
plt.close()

print("Gráfico elbow salvo como elbow.png")

# =========================
# 5. Plot Silhouette (salvar)
# =========================
plt.figure()
plt.plot(k_values, silhouettes, marker='o')
plt.title("Silhouette Score")
plt.xlabel("k")
plt.ylabel("Score")
plt.savefig("silhouette.png")
plt.close()

print("Gráfico silhouette salvo como silhouette.png")

# =========================
# 6. Escolher k automaticamente
# =========================
best_k = 4 #k_values[np.argmax(silhouettes)]

print(f"\nMelhor k baseado no silhouette: {best_k}")

# =========================
# 7. K-means final
# =========================
kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
labels = kmeans.fit_predict(X_scaled)

df["cluster"] = labels

# =========================
# 8. Salvar resultado
# =========================
df.to_csv("features_clustered.csv", index=False)

print("\nClustering finalizado!")
print(f"Número de clusters escolhido: {best_k}")

print("\nDistribuição dos clusters:")
print(df["cluster"].value_counts())

print(df.groupby("cluster").mean(numeric_only=True))

for i in range(0, best_k):
    print(df[df["cluster"] == i]["arquivo"])